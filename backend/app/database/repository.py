import json
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from backend.app.config import settings, config_manager
from backend.app.database.models import (
    Candidate, Education, Employment, Publication, RuleResult, AuditLog, JDEvaluation, JobDescription, SessionLocal, init_db
)
from backend.app.schemas.resume import ResumeProfile
from backend.app.services.education_service import EducationService
from backend.app.utils.json_utils import (
    atomic_write_json,
    atomic_write_text,
    safe_child_path,
    validate_candidate_id,
)

logger = logging.getLogger("FacultyScreen.CandidateRepo")

ALLOWED_SORT_COLUMNS = {
    "overall_score",
    "name",
    "teaching_years",
    "research_years",
    "industry_years",
    "administrative_years",
    "total_years",
    "publications_count",
    "confidence",
    "grounding_score",
    "created_at",
    "updated_at",
}

class CandidateRepository:
    """
    Data repository for candidate profiles, screening results, review queues, and audit logs.
    """

    def __init__(self, db_session_factory=SessionLocal):
        self.session_factory = db_session_factory
        if db_session_factory is SessionLocal:
            init_db()

    def save_profile(self, profile: ResumeProfile, is_uploaded: Optional[bool] = None) -> None:
        """
        Upserts a full ResumeProfile into the relational database.
        """
        session: Session = self.session_factory()
        try:
            # Check if candidate exists
            cand = session.query(Candidate).filter(Candidate.id == profile.candidate_id).first()
            if not cand:
                cand = Candidate(id=profile.candidate_id)
                session.add(cand)

            if is_uploaded is not None:
                cand.is_uploaded = is_uploaded

            # Update scalar fields
            cand.name = profile.name
            cand.email = profile.email
            cand.phone = profile.phone
            cand.location = profile.location
            cand.current_designation = profile.current_designation
            cand.summary = profile.summary

            top_edu = EducationService.select_highest_education(profile.education)
            if top_edu:
                cand.highest_degree = top_edu.normalized_degree
                cand.highest_institution = top_edu.institution_normalized or top_edu.institution
                cand.highest_institution_category = top_edu.institution_category
                cand.institution_tier = top_edu.institution_tier
            else:
                cand.highest_degree = None
                cand.highest_institution = None
                cand.highest_institution_category = None
                cand.institution_tier = None

            cand.teaching_years = profile.experience.teaching_years
            cand.research_years = profile.experience.research_years
            cand.industry_years = profile.experience.industry_years
            cand.administrative_years = profile.experience.administrative_years
            cand.total_years = profile.experience.total_years

            cand.publications_count = len(profile.research.publications)

            cand.eligibility_status = profile.screening.eligibility_status
            cand.overall_score = profile.screening.overall_score
            cand.confidence = profile.screening.confidence
            cand.review_status = profile.review_status
            cand.review_notes = profile.review_notes
            cand.reviewer_verdict = profile.reviewer_verdict

            if profile.metadata:
                cand.file_name = profile.metadata.file_name
                cand.file_path = profile.metadata.file_path
                cand.file_hash = profile.metadata.file_hash
                cand.processing_time_seconds = profile.metadata.processing_time_seconds
                cand.page_count = profile.metadata.page_count
                cand.groq_api_calls = profile.metadata.groq_api_calls
                cand.jev_decision_calls = profile.metadata.jev_decision_calls
                cand.deterministic_resolutions = profile.metadata.deterministic_resolutions
                cand.escalations = profile.metadata.escalations
                cand.grounding_score = profile.metadata.grounding_score
            else:
                cand.file_name = "resume.pdf"
                cand.file_path = ""
                cand.file_hash = ""
                cand.processing_time_seconds = 0.0
                cand.page_count = 1
                cand.groq_api_calls = 0
                cand.jev_decision_calls = 0
                cand.deterministic_resolutions = 0
                cand.escalations = 0
                cand.grounding_score = 1.0

            cand.profile_extras_json = json.dumps({
                "skills": profile.skills,
                "certifications": profile.certifications,
                "awards": profile.awards,
                "projects": profile.projects,
                "courses_taught": [c.model_dump() for c in profile.courses_taught],
                "teaching_interests": profile.teaching_interests,
                "supervision": profile.supervision.model_dump() if profile.supervision else {},
                "academic_service": profile.academic_service,
                "notable_highlights": [h.model_dump() for h in profile.notable_highlights],
                "education_rich": [e.model_dump() for e in profile.education],
                "source_evidence": [ev.model_dump() for ev in profile.source_evidence],
                "research": profile.research.model_dump(),
                "screening_flags": profile.screening.flags,
                "decision_path": profile.screening.decision_path,
                "metadata": profile.metadata.model_dump() if profile.metadata else None,
            })

            cand.courses_taught_count = len(profile.courses_taught)
            cand.has_google_scholar = any(l.platform == "google_scholar" for l in profile.academic_links)
            cand.has_orcid = any(l.platform == "orcid" for l in profile.academic_links)
            cand.academic_links_json = json.dumps([l.model_dump() for l in profile.academic_links])
            if profile.external_verification:
                cand.external_citations = profile.external_verification.citation_count
                cand.external_h_index = profile.external_verification.h_index
                cand.external_verification_json = profile.external_verification.model_dump_json()
            else:
                cand.external_citations = None
                cand.external_h_index = None
                cand.external_verification_json = None

            # Clear previous child entries for fresh sync
            session.query(Education).filter(Education.candidate_id == profile.candidate_id).delete()
            session.query(Employment).filter(Employment.candidate_id == profile.candidate_id).delete()
            session.query(Publication).filter(Publication.candidate_id == profile.candidate_id).delete()
            session.query(RuleResult).filter(RuleResult.candidate_id == profile.candidate_id).delete()

            # Insert Education entries
            for edu in profile.education:
                session.add(Education(
                    candidate_id=profile.candidate_id,
                    degree=edu.degree,
                    normalized_degree=edu.normalized_degree,
                    field=edu.field,
                    institution=edu.institution,
                    institution_normalized=edu.institution_normalized,
                    institution_category=edu.institution_category,
                    institution_tier=edu.institution_tier,
                    graduation_year=edu.graduation_year,
                    confidence=edu.confidence,
                    evidence=edu.evidence,
                    source_page=edu.source_page or 1
                ))

            # Insert Employment entries
            for emp in profile.employment:
                session.add(Employment(
                    candidate_id=profile.candidate_id,
                    title=emp.title,
                    organization=emp.organization,
                    category=emp.category,
                    start_date=emp.start_date,
                    end_date=emp.end_date,
                    duration_years=emp.duration_years,
                    is_current=emp.is_current,
                    description=emp.description,
                    evidence=emp.evidence
                ))

            # Insert Publication entries
            for pub in profile.research.publications:
                session.add(Publication(
                    candidate_id=profile.candidate_id,
                    title=pub.title,
                    venue=pub.venue,
                    year=pub.year,
                    doi=pub.doi,
                    indexed=pub.indexed,
                    evidence=pub.evidence
                ))

            # Insert Rule evaluations
            for r in profile.screening.rules_evaluated:
                session.add(RuleResult(
                    candidate_id=profile.candidate_id,
                    rule_id=r.rule_id,
                    rule_name=r.rule_name if hasattr(r, 'rule_name') and r.rule_name else (r.name if hasattr(r, 'name') else ""),
                    status=r.status,
                    reason=r.reason,
                    evidence=r.evidence,
                    confidence=r.confidence,
                    is_mandatory=r.is_mandatory,
                    weight=r.weight
                ))

            # Add Audit Log
            session.add(AuditLog(
                candidate_id=profile.candidate_id,
                action="PROCESSED_PROFILE",
                details=f"Eligibility: {cand.eligibility_status}, Score: {cand.overall_score}%"
            ))

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        cand_id = validate_candidate_id(candidate_id)
        session = self.session_factory()
        try:
            cand = session.query(Candidate).filter(Candidate.id == cand_id).first()
            if not cand:
                return None
            return self._candidate_to_dict(cand)
        finally:
            session.close()

    def list_all_candidate_ids(self) -> List[str]:
        session = self.session_factory()
        try:
            rows = session.query(Candidate.id).all()
            return [r[0] for r in rows]
        finally:
            session.close()

    def list_candidates(
        self,
        search: Optional[str] = None,
        degree: Optional[str] = None,
        institution_category: Optional[str] = None,
        min_teaching_years: Optional[float] = None,
        eligibility_status: Optional[str] = None,
        review_status: Optional[str] = None,
        uploaded_only: bool = False,
        sort_by: str = "overall_score",
        sort_desc: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        session = self.session_factory()
        try:
            query = session.query(Candidate)

            if uploaded_only:
                query = query.filter(Candidate.is_uploaded == True)

            if search:
                term = f"%{search}%"
                query = query.filter(or_(
                    Candidate.name.ilike(term),
                    Candidate.highest_institution.ilike(term),
                    Candidate.email.ilike(term),
                    Candidate.current_designation.ilike(term)
                ))

            if degree:
                query = query.filter(Candidate.highest_degree == degree)

            if institution_category:
                query = query.filter(Candidate.highest_institution_category == institution_category)

            if min_teaching_years is not None:
                query = query.filter(Candidate.teaching_years >= min_teaching_years)

            if eligibility_status:
                query = query.filter(Candidate.eligibility_status == eligibility_status)

            if review_status:
                query = query.filter(Candidate.review_status == review_status)

            total_count = query.count()

            # Sorting (strictly whitelisted column names)
            safe_sort_key = sort_by if sort_by in ALLOWED_SORT_COLUMNS else "overall_score"
            sort_col = getattr(Candidate, safe_sort_key, Candidate.overall_score)
            query = query.order_by(desc(sort_col) if sort_desc else asc(sort_col))

            items = query.offset(offset).limit(limit).all()
            return [self._candidate_to_dict(c) for c in items], total_count
        finally:
            session.close()

    def get_review_queue(self) -> List[Dict[str, Any]]:
        session = self.session_factory()
        try:
            threshold = float(config_manager.get_review_config()["queue_confidence_threshold"])
            items = session.query(Candidate).filter(
                Candidate.review_status.notin_(["Manually verified", "Disqualified"]),
                or_(
                    Candidate.eligibility_status == "needs_review",
                    Candidate.review_status == "Needs review",
                    Candidate.confidence < threshold
                )
            ).order_by(asc(Candidate.confidence)).all()
            return [self._candidate_to_dict(c) for c in items]
        finally:
            session.close()

    def update_review(self, candidate_id: str, verdict: str, notes: Optional[str] = None) -> bool:
        cand_id = validate_candidate_id(candidate_id)
        session = self.session_factory()
        try:
            cand = session.query(Candidate).filter(Candidate.id == cand_id).first()
            if not cand:
                return False
            new_review_status = "Manually verified" if verdict in ["approved", "eligible"] else "Disqualified"
            new_eligibility = "eligible" if verdict in ["approved", "eligible"] else "disqualified"
            cand.review_status = new_review_status
            cand.reviewer_verdict = verdict
            cand.review_notes = notes
            cand.eligibility_status = new_eligibility

            session.add(AuditLog(
                candidate_id=cand_id,
                action="MANUAL_REVIEW_SUBMITTED",
                actor="recruiter",
                details=f"Verdict: {verdict}. Notes: {notes}"
            ))

            session.commit()

            # Sync manual review decision atomically to processed resume.json and resume.md
            try:
                from backend.app.schemas.resume import ResumeProfile
                from backend.app.utils.markdown_generator import MarkdownGenerator

                processed_dir = safe_child_path(settings.data_dir / "processed", cand_id)
                json_path = processed_dir / "resume.json"
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["review_status"] = new_review_status
                    data["reviewer_verdict"] = verdict
                    data["review_notes"] = notes
                    if isinstance(data.get("screening"), dict):
                        data["screening"]["eligibility_status"] = new_eligibility
                    atomic_write_json(json_path, data)

                    profile = ResumeProfile(**data)
                    md_content = MarkdownGenerator.generate_markdown(profile)
                    atomic_write_text(processed_dir / "resume.md", md_content)
            except Exception as sync_err:
                logger.warning(f"Failed to sync review decision to disk for {cand_id}: {sync_err}")

            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def delete_candidate(self, candidate_id: str) -> bool:
        """
        Deletes a single candidate and all associated child records from DB,
        and safely removes generated data from data/processed/{candidate_id}.
        """
        cand_id = validate_candidate_id(candidate_id)
        session = self.session_factory()
        try:
            session.query(Education).filter(Education.candidate_id == cand_id).delete()
            session.query(Employment).filter(Employment.candidate_id == cand_id).delete()
            session.query(Publication).filter(Publication.candidate_id == cand_id).delete()
            session.query(RuleResult).filter(RuleResult.candidate_id == cand_id).delete()
            session.query(AuditLog).filter(AuditLog.candidate_id == cand_id).delete()
            deleted = session.query(Candidate).filter(Candidate.id == cand_id).delete()
            session.commit()

            cand_dir = safe_child_path(settings.data_dir / "processed", cand_id)
            if cand_dir.exists():
                shutil.rmtree(cand_dir, ignore_errors=True)

            return deleted > 0
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting candidate {cand_id}: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def _clear_directory(target_dir: Path) -> None:
        if not (target_dir.exists() and target_dir.is_dir()):
            return
        for item in target_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file():
                item.unlink(missing_ok=True)

    def clear_all_candidates(self) -> int:
        """
        Clears all candidates, educations, employments, publications, rule results,
        JD evaluations, audit logs, and removes processed/uploaded artifacts.
        Does NOT touch original source PDF files or saved JD definitions.
        """
        return self.reset_workspace(include_jds=False, include_source_resumes=False)["candidates_deleted"]

    def reset_workspace(
        self,
        include_jds: bool = True,
        include_source_resumes: bool = False,
    ) -> Dict[str, int]:
        """
        Full workspace reset for starting from scratch.
        Purges database tables and runtime artifact directories while preserving
        data/institutions/institutions.json and config/*.yaml files.
        """
        session = self.session_factory()
        candidates_deleted = 0
        jds_deleted = 0
        source_files_deleted = 0
        try:
            session.query(JDEvaluation).delete()
            session.query(Education).delete()
            session.query(Employment).delete()
            session.query(Publication).delete()
            session.query(RuleResult).delete()
            session.query(AuditLog).delete()
            candidates_deleted = session.query(Candidate).delete()
            if include_jds:
                jds_deleted = session.query(JobDescription).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error resetting workspace DB: {e}")
            raise
        finally:
            session.close()

        subdirs = ["processed", "uploads", "extracted", "results", "logs"]
        if include_jds:
            subdirs.append("jds")

        for sub in subdirs:
            self._clear_directory(settings.data_dir / sub)

        if include_source_resumes:
            resumes_dir = settings.resumes_dir
            if resumes_dir.exists() and resumes_dir.is_dir():
                for item in resumes_dir.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        item.unlink(missing_ok=True)
                        source_files_deleted += 1

        return {
            "candidates_deleted": candidates_deleted,
            "jds_deleted": jds_deleted,
            "source_files_deleted": source_files_deleted,
        }

    def _load_extras_for_candidate(self, c: Candidate) -> Dict[str, Any]:
        if c.profile_extras_json:
            try:
                loaded = json.loads(c.profile_extras_json)
                if isinstance(loaded, dict):
                    return loaded
            except Exception:
                pass

        # Fallback to processed resume.json for legacy DB rows
        try:
            cand_id = validate_candidate_id(c.id)
            disk_json = safe_child_path(settings.data_dir / "processed", cand_id) / "resume.json"
        except ValueError:
            return {}
        if disk_json.exists():
            try:
                with open(disk_json, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                return {
                    "skills": raw.get("skills", []),
                    "certifications": raw.get("certifications", []),
                    "awards": raw.get("awards", []),
                    "projects": raw.get("projects", []),
                    "source_evidence": raw.get("source_evidence", []),
                    "research": raw.get("research", {}),
                    "screening_flags": (raw.get("screening") or {}).get("flags", []),
                    "decision_path": (raw.get("screening") or {}).get("decision_path", []),
                    "metadata": raw.get("metadata"),
                }
            except Exception:
                pass
        return {}

    def get_telemetry_and_latency_summary(self) -> Dict[str, Any]:
        session = self.session_factory()
        try:
            rows = session.query(Candidate).all()
            if not rows:
                return {
                    "average_processing_time_sec": 0.0,
                    "deterministic_resolutions": 0,
                    "jev_decision_calls": 0,
                    "groq_api_calls": 0,
                    "escalations": 0,
                }

            latencies: List[float] = []
            det_total = 0
            jev_total = 0
            groq_total = 0
            esc_total = 0

            for c in rows:
                proc_t = float(c.processing_time_seconds or 0.0)
                det = int(c.deterministic_resolutions or 0)
                jev = int(c.jev_decision_calls or 0)
                groq = int(c.groq_api_calls or 0)
                esc = int(c.escalations or 0)

                if proc_t == 0.0 and groq == 0 and det == 0:
                    meta_path = settings.data_dir / "processed" / c.id / "metadata.json"
                    if meta_path.exists():
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                m = json.load(f)
                            proc_t = float(m.get("processing_time_seconds") or 0.0)
                            det = int(m.get("deterministic_resolutions") or 0)
                            jev = int(m.get("jev_decision_calls") or 0)
                            groq = int(m.get("groq_api_calls") or 0)
                            esc = int(m.get("escalations") or 0)
                        except Exception:
                            pass

                if proc_t > 0:
                    latencies.append(proc_t)
                det_total += det
                jev_total += jev
                groq_total += groq
                esc_total += esc

            avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
            return {
                "average_processing_time_sec": avg_latency,
                "deterministic_resolutions": det_total,
                "jev_decision_calls": jev_total,
                "groq_api_calls": groq_total,
                "escalations": esc_total,
            }
        finally:
            session.close()

    def _candidate_to_dict(self, c: Candidate) -> Dict[str, Any]:
        extras = self._load_extras_for_candidate(c)
        metadata = extras.get("metadata")
        grounding = c.grounding_score
        if grounding is None and isinstance(metadata, dict):
            grounding = metadata.get("grounding_score", 1.0)
        proc_time = c.processing_time_seconds
        if not proc_time and isinstance(metadata, dict):
            proc_time = metadata.get("processing_time_seconds", 0.0)
        page_cnt = c.page_count
        if (not page_cnt or page_cnt == 1) and isinstance(metadata, dict) and metadata.get("page_count"):
            page_cnt = metadata.get("page_count")

        publications_list = [
            {
                "title": p.title,
                "venue": p.venue,
                "year": p.year,
                "doi": p.doi,
                "indexed": p.indexed,
                "evidence": p.evidence
            } for p in c.publications
        ]
        research_data = extras.get("research") or {}
        if not isinstance(research_data, dict):
            research_data = {}
        research_hydrated = {
            "publications": publications_list,
            "patents": research_data.get("patents", []),
            "research_projects": research_data.get("research_projects", []),
            "research_domains": research_data.get("research_domains", []),
            "books": research_data.get("books", []),
        }

        return {
            "id": c.id,
            "candidate_id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "location": c.location,
            "current_designation": c.current_designation,
            "summary": c.summary,
            "highest_degree": c.highest_degree,
            "highest_institution": c.highest_institution,
            "highest_institution_category": c.highest_institution_category,
            "institution_tier": c.institution_tier,
            "teaching_years": c.teaching_years,
            "research_years": c.research_years,
            "industry_years": c.industry_years,
            "administrative_years": c.administrative_years or 0.0,
            "total_years": c.total_years,
            "publications_count": c.publications_count,
            "eligibility_status": c.eligibility_status,
            "overall_score": c.overall_score,
            "confidence": c.confidence,
            "grounding_score": grounding if grounding is not None else 1.0,
            "processing_time_seconds": proc_time or 0.0,
            "page_count": page_cnt or 1,
            "review_status": c.review_status,
            "review_notes": c.review_notes,
            "reviewer_verdict": c.reviewer_verdict,
            "file_name": c.file_name,
            "file_path": c.file_path,
            "is_uploaded": bool(c.is_uploaded),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "skills": extras.get("skills", []),
            "certifications": extras.get("certifications", []),
            "awards": extras.get("awards", []),
            "projects": extras.get("projects", []),
            "courses_taught": extras.get("courses_taught", []),
            "courses_taught_count": c.courses_taught_count or len(extras.get("courses_taught", [])),
            "teaching_interests": extras.get("teaching_interests", []),
            "supervision": extras.get("supervision") or {
                "phd_completed": 0, "phd_ongoing": 0, "masters_guided": 0, "ug_projects_guided": 0, "details": []
            },
            "academic_service": extras.get("academic_service", []),
            "notable_highlights": extras.get("notable_highlights", []),
            "academic_links": json.loads(c.academic_links_json) if c.academic_links_json else extras.get("academic_links", []),
            "external_verification": json.loads(c.external_verification_json) if c.external_verification_json else None,
            "has_google_scholar": bool(c.has_google_scholar),
            "has_orcid": bool(c.has_orcid),
            "external_citations": c.external_citations,
            "external_h_index": c.external_h_index,
            "source_evidence": extras.get("source_evidence", []),
            "research": research_hydrated,
            "screening_flags": extras.get("screening_flags", []),
            "decision_path": extras.get("decision_path", []),
            "metadata": metadata,
            "education": extras.get("education_rich") or [
                {
                    "degree": e.degree,
                    "normalized_degree": e.normalized_degree,
                    "field": e.field,
                    "institution": e.institution,
                    "institution_normalized": e.institution_normalized,
                    "institution_category": e.institution_category,
                    "institution_tier": e.institution_tier,
                    "graduation_year": e.graduation_year,
                    "confidence": e.confidence,
                    "evidence": e.evidence,
                    "source_page": e.source_page
                } for e in c.educations
            ],
            "employment": [
                {
                    "title": emp.title,
                    "organization": emp.organization,
                    "category": emp.category,
                    "start_date": emp.start_date,
                    "end_date": emp.end_date,
                    "duration_years": emp.duration_years,
                    "is_current": emp.is_current,
                    "description": emp.description,
                    "evidence": emp.evidence
                } for emp in c.employments
            ],
            "publications": publications_list,
            "rules_evaluated": [
                {
                    "rule_id": r.rule_id,
                    "name": r.rule_name,
                    "status": r.status,
                    "reason": r.reason,
                    "evidence": r.evidence,
                    "confidence": r.confidence,
                    "is_mandatory": r.is_mandatory,
                    "weight": r.weight
                } for r in c.rule_results
            ]
        }

    def update_external_verification(
        self,
        candidate_id: str,
        academic_links: List[Dict[str, Any]],
        verification: Dict[str, Any],
    ) -> bool:
        cand_id = validate_candidate_id(candidate_id)
        session = self.session_factory()
        try:
            cand = session.query(Candidate).filter(Candidate.id == cand_id).first()
            if not cand:
                return False
            cand.academic_links_json = json.dumps(academic_links)
            cand.has_google_scholar = any(l.get("platform") == "google_scholar" for l in academic_links)
            cand.has_orcid = any(l.get("platform") == "orcid" for l in academic_links)
            cand.external_verification_json = json.dumps(verification)
            cand.external_citations = verification.get("citation_count")
            cand.external_h_index = verification.get("h_index")
            session.commit()

            try:
                processed_dir = safe_child_path(settings.data_dir / "processed", cand_id)
                json_path = processed_dir / "resume.json"
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["academic_links"] = academic_links
                    data["external_verification"] = verification
                    atomic_write_json(json_path, data)
                    from backend.app.utils.markdown_generator import MarkdownGenerator

                    atomic_write_text(processed_dir / "resume.md", MarkdownGenerator.generate_markdown(ResumeProfile(**data)))
            except Exception as disk_err:
                logger.warning(f"Failed syncing enriched links to disk for {cand_id}: {disk_err}")
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()


candidate_repo = CandidateRepository()
