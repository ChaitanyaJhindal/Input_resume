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
    ResumeProfile, EducationEntry, EmploymentEntry, ExperienceBreakdown,
    ProcessingMetadata, SourceEvidence
)
from backend.app.integrations.groq.groq_extractor import groq_extractor
from backend.app.services.education_service import EducationService
from backend.app.services.institution_service import institution_service
from backend.app.services.experience_service import ExperienceService
from backend.app.services.research_service import ResearchService
from backend.app.services.screening_service import screening_service
from backend.app.services.jev.jev_router import jev_router
from backend.app.services.jev.jev_decisions import JevDecisions
from backend.app.utils.markdown_generator import MarkdownGenerator

logger = logging.getLogger("FacultyScreen.Orchestrator")

class ResumeProcessingOrchestrator:
    """
    Central orchestration pipeline for FacultyScreen:
    INGEST -> EXTRACT -> NORMALIZE -> CLASSIFY -> VALIDATE -> SCREEN -> CURATE -> STORE
    """

    def __init__(self, resumes_dir: Optional[str] = None, data_dir: Optional[Path] = None):
        self.resumes_dir = Path(resumes_dir or settings.resumes_dir).resolve()
        self.data_dir = Path(data_dir or settings.data_dir).resolve()
        self.processed_dir = self.data_dir / "processed"
        self.results_dir = self.data_dir / "results"
        self.logs_dir = self.data_dir / "logs"

        # Ensure directory structure exists without touching original resumes folder
        for d in [self.processed_dir, self.results_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_candidate_id(file_path: Path) -> str:
        """
        Creates a deterministic candidate ID based on relative path and filename.
        Preserves stability across restarts.
        """
        seed = f"{file_path.name}_{file_path.stat().st_size}"
        h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
        return f"cand_{h}"

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def discover_resumes(self) -> List[Path]:
        """
        Recursively scans the configured source-of-truth directory for supported documents.
        Supports PDF, PNG, JPG, JPEG.
        Does NOT scan generated data or virtual environments.
        """
        supported_exts = {".pdf", ".png", ".jpg", ".jpeg"}
        found_files = []

        if not self.resumes_dir.exists():
            logger.warning(f"Configured resumes directory does not exist: {self.resumes_dir}")
            return []

        for p in self.resumes_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in supported_exts:
                # Exclude virtual environments or output data directories
                rel_parts = p.relative_to(self.resumes_dir).parts
                if any(ignored in rel_parts for ignored in [".venv", "venv", "data", "apps", "backend", "tests", "paddle_env", "node_modules", ".git"]):
                    continue
                found_files.append(p)

        found_files.sort(key=lambda x: x.name)
        return found_files

    def process_resume(self, file_path: Path, force_reprocess: bool = False) -> ResumeProfile:
        """
        Processes an individual resume through the entire pipeline.
        Writes all output files to data/processed/{candidate_id}/
        """
        start_time = time.time()
        file_hash = self.compute_file_hash(file_path)
        candidate_id = self.generate_candidate_id(file_path)
        cand_output_dir = self.processed_dir / candidate_id
        cand_output_dir.mkdir(parents=True, exist_ok=True)

        cached_json_path = cand_output_dir / "resume.json"

        # Check for cached processing if not forcing reprocess
        if not force_reprocess and cached_json_path.exists():
            try:
                with open(cached_json_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                metadata = cached_data.get("metadata", {})
                if metadata.get("file_hash") == file_hash:
                    logger.info(f"Reusing cached processing for {file_path.name} (Candidate ID: {candidate_id})")
                    return ResumeProfile(**cached_data)
            except Exception as e:
                logger.debug(f"Cache read error for {candidate_id}: {e}. Reprocessing.")

        logger.info(f"--- Starting Pipeline for {file_path.name} ({candidate_id}) ---")

        # STAGE 1: INGEST
        page_count = 1
        if file_path.suffix.lower() == ".pdf":
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(str(file_path))
                page_count = len(doc)
                doc.close()
            except Exception:
                page_count = 1

        # STAGE 2: EXTRACT (Groq Multimodal Vision or Fallback)
        raw_facts = groq_extractor.extract_document(file_path)

        # STAGE 3: NORMALIZE & CLASSIFY EDUCATION & INSTITUTIONS
        education_entries: List[EducationEntry] = []
        raw_edu = raw_facts.get("education", [])
        for edu in raw_edu:
            degree_str = str(edu.get("degree") or "").strip() or "Unspecified Degree"
            inst_str = str(edu.get("institution") or "").strip() or "Unspecified Institution"

            # JEV / Deterministic Degree Level
            norm_degree, deg_conf = JevDecisions.resolve_degree_level(degree_str)

            # JEV / Deterministic Institution Taxonomy
            norm_inst, inst_cat, inst_tier, inst_conf = JevDecisions.resolve_institution_category(inst_str)

            entry = EducationEntry(
                degree=degree_str,
                normalized_degree=norm_degree,
                field=edu.get("field"),
                institution=inst_str,
                institution_normalized=norm_inst,
                institution_category=inst_cat,
                institution_tier=inst_tier,
                graduation_year=edu.get("graduation_year"),
                confidence=round((deg_conf + inst_conf) / 2.0, 2),
                evidence=edu.get("evidence") or f"{degree_str} from {inst_str}",
                source_page=edu.get("source_page", 1)
            )
            education_entries.append(entry)

        # STAGE 4: CLASSIFY EXPERIENCE
        raw_employment = raw_facts.get("employment", [])
        employment_entries: List[EmploymentEntry] = []
        for emp in raw_employment:
            title = str(emp.get("title") or "").strip() or "Role"
            org = str(emp.get("organization") or "").strip() or "Organization"
            cat = emp.get("category") or ExperienceService.categorize_employment(title, org, emp.get("description", ""))

            dur = emp.get("duration_years")
            duration_val = float(dur) if dur is not None else 0.0

            entry = EmploymentEntry(
                title=title,
                organization=org,
                category=cat,
                start_date=str(emp.get("start_date") or ""),
                end_date=str(emp.get("end_date") or ""),
                duration_years=duration_val,
                is_current=bool(emp.get("is_current", False)),
                description=emp.get("description"),
                evidence=emp.get("evidence"),
                source_page=emp.get("source_page", 1)
            )
            employment_entries.append(entry)

        experience_breakdown = ExperienceService.calculate_experience(employment_entries)

        # STAGE 5: RESEARCH & SCHOLARSHIP
        research_profile = ResearchService.process_research_profile(raw_facts.get("research", {}))

        # STAGE 6: SOURCE EVIDENCE COMPILATION
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

        # Temporary profile for rule evaluation
        preliminary_profile = ResumeProfile(
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

        # STAGE 7: SCREENING RULE ENGINE
        screening_res = screening_service.evaluate_candidate(preliminary_profile)
        preliminary_profile.screening = screening_res

        # Determine Review Status
        if screening_res.eligibility_status == "needs_review":
            preliminary_profile.review_status = "Needs review"
        elif screening_res.confidence >= 0.90:
            preliminary_profile.review_status = "High confidence"
        else:
            preliminary_profile.review_status = "Automatically processed"

        # STAGE 8: METADATA & TELEMETRY
        proc_time = round(time.time() - start_time, 2)
        telemetry = jev_router.get_telemetry()
        metadata = ProcessingMetadata(
            pipeline_version="1.0.0",
            model_name=settings.groq_vision_model,
            file_name=file_path.name,
            file_path=str(file_path.resolve()),
            file_hash=file_hash,
            page_count=page_count,
            processing_time_seconds=proc_time,
            groq_api_calls=1 if groq_extractor.is_available else 0,
            jev_decision_calls=telemetry.get("jev_decision_calls", 0),
            deterministic_resolutions=telemetry.get("deterministic_resolutions", 0),
            processed_at=datetime.utcnow().isoformat() + "Z"
        )
        preliminary_profile.metadata = metadata

        # STAGE 9: GENERATE OUTPUT ARTIFACTS
        # 1. original_reference.json
        original_ref = {
            "candidate_id": candidate_id,
            "original_filename": file_path.name,
            "original_path": str(file_path.resolve()),
            "file_size_bytes": file_path.stat().st_size,
            "file_hash_sha256": file_hash,
            "ingested_at": metadata.processed_at
        }
        with open(cand_output_dir / "original_reference.json", "w", encoding="utf-8") as f:
            json.dump(original_ref, f, indent=2)

        # 2. resume.json (canonical machine-readable)
        with open(cand_output_dir / "resume.json", "w", encoding="utf-8") as f:
            json.dump(preliminary_profile.model_dump(), f, indent=2)

        # 3. resume.md (human-readable Markdown)
        md_content = MarkdownGenerator.generate_markdown(preliminary_profile)
        with open(cand_output_dir / "resume.md", "w", encoding="utf-8") as f:
            f.write(md_content)

        # 4. metadata.json
        with open(cand_output_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        logger.info(f"--- Completed Pipeline for {file_path.name} in {proc_time}s ---")
        return preliminary_profile

    def process_all_resumes(self, force_reprocess: bool = False, max_count: Optional[int] = None) -> List[ResumeProfile]:
        """
        Discovers and processes all candidate resumes in the source-of-truth directory.
        """
        files = self.discover_resumes()
        if max_count:
            files = files[:max_count]

        profiles = []
        logger.info(f"Processing {len(files)} discovered resume files...")
        for p in files:
            try:
                prof = self.process_resume(p, force_reprocess=force_reprocess)
                profiles.append(prof)
            except Exception as e:
                logger.error(f"Failed to process {p.name}: {e}", exc_info=True)

        return profiles

orchestrator = ResumeProcessingOrchestrator()
