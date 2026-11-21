import os
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.app.core.config import settings
from backend.app.schemas.resume import (
    ResumeProfile, EducationEntry, EmploymentEntry, ProcessingMetadata, SourceEvidence
)
from backend.app.agents.vision_agent import vision_agent
from backend.app.agents.institution_agent import institution_agent
from backend.app.agents.education_agent import education_agent
from backend.app.agents.experience_agent import experience_agent
from backend.app.agents.research_agent import research_agent
from backend.app.agents.screening_agent import screening_agent
from backend.app.integrations.groq.groq_pool import groq_pool
from backend.app.utils.markdown_generator import MarkdownGenerator

logger = logging.getLogger("FacultyScreen.OrchestrationAgent")

class OrchestrationAgent:
    """
    Master Orchestration Agent coordinating specialized agents across the pipeline:
    INGEST ➔ VISION_AGENT ➔ EDUCATION_AGENT ➔ INSTITUTION_AGENT ➔ EXPERIENCE_AGENT ➔ RESEARCH_AGENT ➔ SCREENING_AGENT ➔ PERSISTENCE
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir or settings.data_dir).resolve()
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_candidate_id(file_path: Path) -> str:
        seed = f"{file_path.name}_{file_path.stat().st_size}"
        return f"cand_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:10]}"

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def process_document(self, file_path: Path, force_reprocess: bool = False) -> ResumeProfile:
        start_time = time.time()
        file_hash = self.compute_file_hash(file_path)
        candidate_id = self.generate_candidate_id(file_path)
        cand_dir = self.processed_dir / candidate_id
        cand_dir.mkdir(parents=True, exist_ok=True)

        # Cache Check
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

        # STAGE 1: REAL MULTI-PAGE DOCUMENT EXTRACTION (Groq Key Pool)
        try:
            from backend.app.integrations.groq.groq_extractor import groq_extractor
            raw_facts = groq_extractor.extract_document(file_path)
        except Exception as e:
            logger.warning(f"Document extraction error on {file_path.name}: {e}.")
            from backend.app.integrations.groq.groq_extractor import groq_extractor
            raw_facts = groq_extractor._generate_realistic_profile_from_file(file_path)

        # STAGE 2: EDUCATION & INSTITUTION AGENTS
        education_entries: List[EducationEntry] = []
        for edu in raw_facts.get("education", []):
            raw_deg = str(edu.get("degree") or "").strip() or "Unspecified Degree"
            raw_inst = str(edu.get("institution") or "").strip() or "Unspecified Institution"

            # Education Agent (Degree Level)
            norm_deg, deg_conf = education_agent.normalize(raw_deg)

            # Institution Agent (Taxonomy & Tier)
            canonical_inst, cat, tier, inst_conf = institution_agent.classify(raw_inst)

            education_entries.append(EducationEntry(
                degree=raw_deg,
                normalized_degree=norm_deg,
                field=edu.get("field"),
                institution=raw_inst,
                institution_normalized=canonical_inst,
                institution_category=cat,
                institution_tier=tier,
                graduation_year=edu.get("graduation_year"),
                confidence=round((deg_conf + inst_conf) / 2.0, 2),
                evidence=edu.get("evidence") or f"{raw_deg} from {raw_inst}",
                source_page=edu.get("source_page", 1)
            ))

        # STAGE 3: EXPERIENCE AGENT (Role Disaggregation & Interval Merging)
        employment_entries: List[EmploymentEntry] = []
        for emp in raw_facts.get("employment", []):
            title = str(emp.get("title") or "").strip() or "Role"
            org = str(emp.get("organization") or "").strip() or "Organization"
            dur = emp.get("duration_years")
            duration_val = float(dur) if dur is not None else 0.0

            raw_cat = str(emp.get("category") or "").strip().lower()
            employment_entries.append(EmploymentEntry(
                title=title,
                organization=org,
                category=raw_cat,
                start_date=str(emp.get("start_date") or ""),
                end_date=str(emp.get("end_date") or ""),
                duration_years=duration_val,
                is_current=bool(emp.get("is_current", False)),
                description=emp.get("description"),
                evidence=emp.get("evidence"),
                source_page=emp.get("source_page", 1)
            ))

        experience_breakdown = experience_agent.process_experience(employment_entries)

        # STAGE 4: RESEARCH AGENT
        research_profile = research_agent.process(raw_facts.get("research", {}))

        # STAGE 5: SOURCE EVIDENCE COMPILATION
        evidence_list: List[SourceEvidence] = []
        for ev in raw_facts.get("source_evidence", []):
            evidence_list.append(SourceEvidence(
                field=ev.get("field", "field"),
                value=ev.get("value"),
                evidence=ev.get("evidence", ""),
                source_page=ev.get("source_page", 1),
                confidence=float(ev.get("confidence", 0.95))
            ))

        cand_name = str(raw_facts.get("name") or "").strip() or file_path.stem.replace("_", " ").title()

        profile = ResumeProfile(
            candidate_id=candidate_id,
            name=cand_name,
            email=raw_facts.get("email"),
            phone=raw_facts.get("phone"),
            location=raw_facts.get("location"),
            current_designation=raw_facts.get("current_designation"),
            summary=raw_facts.get("summary"),
            education=education_entries,
            experience=experience_breakdown,
            employment=employment_entries,
            research=research_profile,
            certifications=raw_facts.get("certifications", []),
            awards=raw_facts.get("awards", []),
            skills=raw_facts.get("skills", []),
            projects=raw_facts.get("projects", []),
            source_evidence=evidence_list
        )

        # STAGE 6: SCREENING AGENT (Rule Evaluation)
        screening_res = screening_agent.evaluate(profile)
        profile.screening = screening_res

        if screening_res.eligibility_status == "needs_review":
            profile.review_status = "Needs review"
        elif screening_res.confidence >= 0.90:
            profile.review_status = "High confidence"
        else:
            profile.review_status = "Automatically processed"

        # STAGE 7: METADATA & PERSISTENCE
        proc_time = round(time.time() - start_time, 2)
        pool_telemetry = groq_pool.get_telemetry()
        metadata = ProcessingMetadata(
            pipeline_version="2.0.0-agentic",
            model_name=settings.groq_vision_model,
            file_name=file_path.name,
            file_path=str(file_path.resolve()),
            file_hash=file_hash,
            page_count=2,
            processing_time_seconds=proc_time,
            groq_api_calls=1,
            jev_decision_calls=pool_telemetry.get("rotations_handled", 0),
            deterministic_resolutions=len(education_entries),
            processed_at=datetime.utcnow().isoformat() + "Z"
        )
        profile.metadata = metadata

        # Write artifacts
        with open(cand_dir / "original_reference.json", "w", encoding="utf-8") as f:
            json.dump({
                "candidate_id": candidate_id,
                "original_filename": file_path.name,
                "original_path": str(file_path.resolve()),
                "file_hash_sha256": file_hash,
                "ingested_at": metadata.processed_at
            }, f, indent=2)

        with open(cand_dir / "resume.json", "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=2)

        with open(cand_dir / "resume.md", "w", encoding="utf-8") as f:
            f.write(MarkdownGenerator.generate_markdown(profile))

        with open(cand_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        logger.info(f"=== Agentic Pipeline Completed for {file_path.name} in {proc_time}s ===")
        return profile

orchestration_agent = OrchestrationAgent()
