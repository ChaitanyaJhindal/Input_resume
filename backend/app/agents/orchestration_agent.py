import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.app.config import settings, config_manager
from backend.app.schemas.resume import (
    AcademicLink,
    CourseTaughtEntry,
    EducationEntry,
    EmploymentEntry,
    NotableHighlight,
    ProcessingMetadata,
    ResumeProfile,
    ScreeningResult,
    SourceEvidence,
    SupervisionSummary,
)
from backend.app.agents.institution_agent import institution_agent
from backend.app.agents.education_agent import education_agent
from backend.app.agents.experience_agent import experience_agent
from backend.app.agents.research_agent import research_agent
from backend.app.agents.screening_agent import screening_agent
from backend.app.groq.extractor import groq_extractor
from backend.app.services.academic_profile_service import academic_profile_service
from backend.app.services.education_service import EducationService
from backend.app.services.experience_service import ExperienceService
from backend.app.services.validation_service import ValidationService
from backend.app.utils.link_extractor import extract_academic_links
from backend.app.utils.json_utils import (
    atomic_write_json,
    atomic_write_text,
    safe_dict_list,
    safe_float,
    safe_int,
    safe_str_list,
)
from backend.app.utils.markdown_generator import MarkdownGenerator

logger = logging.getLogger("FacultyScreen.OrchestrationAgent")


class OrchestrationAgent:
    """
    Master Orchestration Agent coordinating specialized agents across the pipeline:
    INGEST -> EXTRACT -> EDUCATION_AGENT -> INSTITUTION_AGENT -> EXPERIENCE_AGENT -> RESEARCH_AGENT -> VALIDATION -> SCREENING_AGENT -> PERSISTENCE
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir or settings.data_dir).resolve()
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def generate_candidate_id(file_path: Path, file_hash: Optional[str] = None) -> str:
        h = file_hash or OrchestrationAgent.compute_file_hash(file_path)
        return f"cand_{h[:10]}"

    @staticmethod
    def _to_stored_path(file_path: Path) -> str:
        resolved = file_path.resolve()
        try:
            return resolved.relative_to(settings.base_dir.resolve()).as_posix()
        except ValueError:
            return str(resolved)

    @staticmethod
    def _tally_tier_source(
        tier_source: str,
        det_count: int,
        jev_count: int,
        esc_count: int,
        groq_count: int,
    ) -> tuple[int, int, int, int]:
        if tier_source == "deterministic":
            return det_count + 1, jev_count, esc_count, groq_count
        if tier_source == "jev":
            return det_count, jev_count + 1, esc_count, groq_count
        if tier_source == "groq_escalation":
            return det_count, jev_count + 1, esc_count + 1, groq_count + 1
        return det_count, jev_count + 1, esc_count + 1, groq_count

    def process_document(self, file_path: Path, force_reprocess: bool = False) -> ResumeProfile:
        start_time = time.time()
        file_hash = self.compute_file_hash(file_path)
        candidate_id = self.generate_candidate_id(file_path, file_hash=file_hash)
        cand_dir = self.processed_dir / candidate_id
        cand_dir.mkdir(parents=True, exist_ok=True)

        cached_json = cand_dir / "resume.json"
        if not force_reprocess and cached_json.exists():
            try:
                with open(cached_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("metadata", {}).get("file_hash") == file_hash:
                    logger.info(f"Reusing cached extraction for {file_path.name}")
                    return ResumeProfile(**data)
            except Exception:
                pass

        logger.info(f"=== Agentic Pipeline Initiated for {file_path.name} ({candidate_id}) ===")

        # STAGE 1: REAL MULTI-PAGE DOCUMENT EXTRACTION
        raw_facts = groq_extractor.extract_document(file_path)
        raw_text = str(raw_facts.get("_raw_text") or "")
        page_count = max(1, safe_int(raw_facts.get("_page_count"), 1) or 1)
        groq_calls = safe_int(raw_facts.get("_groq_calls"), 0) or 0
        extraction_method = str(raw_facts.get("_extraction_method") or "groq_text")
        model_used = str(raw_facts.get("_model_used") or config_manager.resolve_model("reasoning"))
        json_repaired = bool(raw_facts.get("_json_repaired", False))

        # STAGE 2: EDUCATION & INSTITUTION AGENTS (Unified 3-tier JevRouter)
        deterministic_resolutions = 0
        jev_decision_calls = 0
        escalations = 0
        education_entries: List[EducationEntry] = []

        for edu in safe_dict_list(raw_facts.get("education"), fallback_key="degree"):
            raw_deg = str(edu.get("degree") or "").strip() or "Unspecified Degree"
            raw_inst = str(edu.get("institution") or "").strip() or "Unspecified Institution"

            norm_deg, deg_conf, deg_source = education_agent.normalize_detailed(raw_deg)
            deterministic_resolutions, jev_decision_calls, escalations, groq_calls = self._tally_tier_source(
                deg_source, deterministic_resolutions, jev_decision_calls, escalations, groq_calls
            )

            canonical_inst, cat, tier, inst_conf, inst_source = institution_agent.classify_detailed(raw_inst)
            deterministic_resolutions, jev_decision_calls, escalations, groq_calls = self._tally_tier_source(
                inst_source, deterministic_resolutions, jev_decision_calls, escalations, groq_calls
            )

            field_raw = edu.get("field")
            ev_raw = edu.get("evidence")
            thesis_raw = edu.get("thesis_title")
            advisor_raw = edu.get("advisor")
            gpa_raw = edu.get("gpa_or_honors")
            edu_status = str(edu.get("status") or "").strip().lower()
            if edu_status not in {"completed", "in_progress"}:
                edu_status = "in_progress" if norm_deg == "PhD (In Progress)" else "completed"

            education_entries.append(
                EducationEntry(
                    degree=raw_deg,
                    normalized_degree=norm_deg,
                    field=str(field_raw).strip() if field_raw is not None and str(field_raw).strip() else None,
                    institution=raw_inst,
                    institution_normalized=canonical_inst,
                    institution_category=cat,
                    institution_tier=tier,
                    start_year=safe_int(edu.get("start_year")),
                    graduation_year=safe_int(edu.get("graduation_year")),
                    thesis_title=str(thesis_raw).strip() if thesis_raw is not None and str(thesis_raw).strip() else None,
                    advisor=str(advisor_raw).strip() if advisor_raw is not None and str(advisor_raw).strip() else None,
                    gpa_or_honors=str(gpa_raw).strip() if gpa_raw is not None and str(gpa_raw).strip() else None,
                    status=edu_status,
                    confidence=round((deg_conf + inst_conf) / 2.0, 2),
                    evidence=str(ev_raw).strip() if ev_raw is not None and str(ev_raw).strip() else None,
                    source_page=max(1, safe_int(edu.get("source_page"), 1) or 1),
                )
            )

        education_entries = EducationService.sort_by_highest_degree(education_entries)

        # STAGE 3: EXPERIENCE AGENT (Unified 3-tier role disaggregation & interval merging)
        employment_entries: List[EmploymentEntry] = []
        for emp in safe_dict_list(raw_facts.get("employment"), fallback_key="title"):
            title = str(emp.get("title") or "").strip() or "Role"
            org = str(emp.get("organization") or "").strip() or "Organization"
            duration_val = max(0.0, safe_float(emp.get("duration_years"), 0.0))
            raw_cat = str(emp.get("category") or "").strip().lower()
            desc_raw = emp.get("description")
            ev_raw = emp.get("evidence")

            employment_entries.append(
                EmploymentEntry(
                    title=title,
                    organization=org,
                    category=raw_cat,
                    start_date=str(emp.get("start_date") or "").strip(),
                    end_date=str(emp.get("end_date") or "").strip(),
                    duration_years=duration_val,
                    is_current=bool(emp.get("is_current", False)),
                    description=str(desc_raw).strip() if desc_raw is not None and str(desc_raw).strip() else None,
                    evidence=str(ev_raw).strip() if ev_raw is not None and str(ev_raw).strip() else None,
                    source_page=max(1, safe_int(emp.get("source_page"), 1) or 1),
                )
            )

        experience_breakdown, exp_tele = experience_agent.process_experience_with_meta(employment_entries)
        deterministic_resolutions += exp_tele["deterministic_resolutions"]
        jev_decision_calls += exp_tele["jev_decision_calls"]
        escalations += exp_tele["escalations"]
        groq_calls += exp_tele["groq_api_calls"]

        # STAGE 4: RESEARCH AGENT
        research_profile = research_agent.process(raw_facts.get("research") or {})

        # STAGE 5: SOURCE EVIDENCE COMPILATION
        evidence_list: List[SourceEvidence] = []
        for ev in safe_dict_list(raw_facts.get("source_evidence"), fallback_key="evidence"):
            evidence_list.append(
                SourceEvidence(
                    field=str(ev.get("field") or "field"),
                    value=ev.get("value"),
                    evidence=str(ev.get("evidence") or ""),
                    source_page=max(1, safe_int(ev.get("source_page"), 1) or 1),
                    confidence=max(0.0, min(1.0, safe_float(ev.get("confidence"), 0.95))),
                )
            )

        cand_name = str(raw_facts.get("name") or "").strip() or file_path.stem.replace("_", " ").title()

        def _opt_str(key: str) -> Optional[str]:
            v = raw_facts.get(key)
            return str(v).strip() if v is not None and str(v).strip() else None

        # Enriched teaching courses, supervision, highlights & deterministic academic links
        courses_list: List[CourseTaughtEntry] = []
        for c_item in safe_dict_list(raw_facts.get("courses_taught"), fallback_key="course_name"):
            cname = str(c_item.get("course_name") or c_item.get("name") or "").strip()
            if not cname:
                continue
            raw_lvl = str(c_item.get("level") or "Unspecified").strip()
            courses_list.append(
                CourseTaughtEntry(
                    course_name=cname,
                    course_code=str(c_item.get("course_code")).strip() if c_item.get("course_code") else None,
                    level=raw_lvl if raw_lvl in {"UG", "PG", "PhD", "Executive", "Unspecified"} else "Unspecified",
                    institution=str(c_item.get("institution")).strip() if c_item.get("institution") else None,
                    term_or_years=str(c_item.get("term_or_years")).strip() if c_item.get("term_or_years") else None,
                    role=str(c_item.get("role") or "Instructor").strip() or "Instructor",
                    evidence=str(c_item.get("evidence")).strip() if c_item.get("evidence") else None,
                    source_page=max(1, safe_int(c_item.get("source_page"), 1) or 1),
                )
            )

        raw_sup = raw_facts.get("supervision") if isinstance(raw_facts.get("supervision"), dict) else {}
        supervision = SupervisionSummary(
            phd_completed=max(0, safe_int(raw_sup.get("phd_completed"), 0) or 0),
            phd_ongoing=max(0, safe_int(raw_sup.get("phd_ongoing"), 0) or 0),
            masters_guided=max(0, safe_int(raw_sup.get("masters_guided"), 0) or 0),
            ug_projects_guided=max(0, safe_int(raw_sup.get("ug_projects_guided"), 0) or 0),
            details=safe_str_list(raw_sup.get("details")),
        )

        highlights_list: List[NotableHighlight] = []
        for h_item in safe_dict_list(raw_facts.get("notable_highlights"), fallback_key="title"):
            htitle = str(h_item.get("title") or "").strip()
            if not htitle:
                continue
            highlights_list.append(
                NotableHighlight(
                    category=str(h_item.get("category") or "achievement").strip().lower(),
                    title=htitle,
                    impact=str(h_item.get("impact")).strip() if h_item.get("impact") else None,
                    evidence=str(h_item.get("evidence")).strip() if h_item.get("evidence") else None,
                )
            )

        raw_links = raw_facts.get("_academic_links")
        if isinstance(raw_links, list):
            academic_links = [AcademicLink(**lnk) for lnk in raw_links if isinstance(lnk, dict) and lnk.get("url")]
        else:
            academic_links = extract_academic_links(file_path, raw_text)

        profile = ResumeProfile(
            candidate_id=candidate_id,
            name=cand_name,
            email=_opt_str("email"),
            phone=_opt_str("phone"),
            location=_opt_str("location"),
            current_designation=_opt_str("current_designation"),
            summary=_opt_str("summary"),
            education=education_entries,
            experience=experience_breakdown,
            employment=employment_entries,
            research=research_profile,
            certifications=safe_str_list(raw_facts.get("certifications")),
            awards=safe_str_list(raw_facts.get("awards")),
            skills=safe_str_list(raw_facts.get("skills")),
            courses_taught=courses_list,
            teaching_interests=safe_str_list(raw_facts.get("teaching_interests")),
            academic_links=academic_links,
            supervision=supervision,
            academic_service=safe_str_list(raw_facts.get("academic_service")),
            notable_highlights=highlights_list,
            projects=safe_dict_list(raw_facts.get("projects")),
            source_evidence=evidence_list,
        )

        # STAGE 6: ANTI-HALLUCINATION VALIDATION & GROUNDING CHECK
        val_report = ValidationService.validate_and_clean(
            profile, raw_text=raw_text, extraction_meta=raw_facts
        )
        if val_report.employment_modified:
            profile.experience = ExperienceService.calculate_experience(profile.employment)

        # Official External Academic Verification (ORCID / OpenAlex via ORCID or DOI)
        if extraction_method != "failed":
            profile.external_verification = academic_profile_service.enrich_profile(profile)

        # STAGE 7: SCREENING AGENT (Rule Evaluation)
        review_cfg = config_manager.get_review_config()
        pipeline_cfg = config_manager.get_pipeline_config()
        high_conf_threshold = float(review_cfg["high_confidence_threshold"])

        if val_report.extraction_failed:
            profile.screening = ScreeningResult(
                eligibility_status="needs_review",
                overall_score=0.0,
                confidence=0.0,
                flags=list(val_report.flags),
                rules_evaluated=[],
                decision_path=["[ERROR] Extraction failed in live mode; routed for manual review"],
            )
            profile.review_status = "Needs review"
        else:
            screening_res = screening_agent.evaluate(profile)
            for vflag in val_report.flags:
                if vflag not in screening_res.flags:
                    screening_res.flags.append(vflag)

            if val_report.json_repaired or val_report.grounding_score < 0.75:
                screening_res.confidence = round(
                    min(screening_res.confidence, val_report.grounding_score, 0.75), 2
                )
                if screening_res.eligibility_status == "eligible":
                    screening_res.eligibility_status = "needs_review"

            profile.screening = screening_res

            if screening_res.eligibility_status == "needs_review":
                profile.review_status = "Needs review"
            elif screening_res.confidence >= high_conf_threshold:
                profile.review_status = "High confidence"
            else:
                profile.review_status = "Automatically processed"

        # STAGE 8: METADATA & ATOMIC PERSISTENCE
        proc_time = round(time.time() - start_time, 2)
        stored_path = self._to_stored_path(file_path)
        processed_at_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        metadata = ProcessingMetadata(
            pipeline_version=pipeline_cfg["agentic_version"],
            model_name=model_used,
            file_name=file_path.name,
            file_path=stored_path,
            file_hash=file_hash,
            page_count=page_count,
            processing_time_seconds=proc_time,
            groq_api_calls=groq_calls,
            jev_decision_calls=jev_decision_calls,
            deterministic_resolutions=deterministic_resolutions,
            escalations=escalations,
            grounding_score=val_report.grounding_score,
            extraction_method=extraction_method,
            json_repaired=json_repaired,
            processed_at=processed_at_iso,
        )
        profile.metadata = metadata

        atomic_write_json(
            cand_dir / "original_reference.json",
            {
                "candidate_id": candidate_id,
                "original_filename": file_path.name,
                "original_path": stored_path,
                "file_size_bytes": file_path.stat().st_size,
                "file_hash_sha256": file_hash,
                "ingested_at": processed_at_iso,
            },
        )
        atomic_write_json(cand_dir / "resume.json", profile.model_dump())
        atomic_write_text(cand_dir / "resume.md", MarkdownGenerator.generate_markdown(profile))
        atomic_write_json(cand_dir / "metadata.json", metadata.model_dump())

        logger.info(f"=== Agentic Pipeline Completed for {file_path.name} in {proc_time}s ===")
        return profile


orchestration_agent = OrchestrationAgent()
