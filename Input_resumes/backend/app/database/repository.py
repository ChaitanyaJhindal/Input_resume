import json
import shutil
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from backend.app.config import settings
from backend.app.database.models import (
    Candidate, Education, Employment, Publication, RuleResult, AuditLog, SessionLocal
)
from backend.app.schemas.resume import ResumeProfile

logger = logging.getLogger("FacultyScreen.CandidateRepo")

class CandidateRepository:
    """
    Data repository for candidate profiles, screening results, review queues, and audit logs.
    """

    def __init__(self, db_session_factory=SessionLocal):
        self.session_factory = db_session_factory

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

            if profile.education:
                top_edu = profile.education[0]
                cand.highest_degree = top_edu.normalized_degree
                cand.highest_institution = top_edu.institution_normalized or top_edu.institution
                cand.highest_institution_category = top_edu.institution_category
                cand.institution_tier = top_edu.institution_tier

            cand.teaching_years = profile.experience.teaching_years
            cand.research_years = profile.experience.research_years
            cand.industry_years = profile.experience.industry_years
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
            else:
                cand.file_name = "resume.pdf"
                cand.file_path = ""
                cand.file_hash = ""

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
        session = self.session_factory()
        try:
            cand = session.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not cand:
                return None
            return self._candidate_to_dict(cand)
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

            # Sorting
            sort_col = getattr(Candidate, sort_by, Candidate.overall_score)
            query = query.order_by(desc(sort_col) if sort_desc else asc(sort_col))

            items = query.offset(offset).limit(limit).all()
            return [self._candidate_to_dict(c) for c in items], total_count
        finally:
            session.close()

    def get_review_queue(self) -> List[Dict[str, Any]]:
        session = self.session_factory()
        try:
            items = session.query(Candidate).filter(
                or_(
                    Candidate.eligibility_status == "needs_review",
                    Candidate.review_status == "Needs review",
                    Candidate.confidence < 0.85
                )
            ).order_by(asc(Candidate.confidence)).all()
            return [self._candidate_to_dict(c) for c in items]
        finally:
            session.close()

    def update_review(self, candidate_id: str, verdict: str, notes: Optional[str] = None) -> bool:
        session = self.session_factory()
        try:
            cand = session.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not cand:
                return False
            cand.review_status = "Manually verified" if verdict in ["approved", "eligible"] else "Disqualified"
            cand.reviewer_verdict = verdict
            cand.review_notes = notes
            cand.eligibility_status = "eligible" if verdict in ["approved", "eligible"] else "disqualified"

            session.add(AuditLog(
                candidate_id=candidate_id,
                action="MANUAL_REVIEW_SUBMITTED",
                actor="recruiter",
                details=f"Verdict: {verdict}. Notes: {notes}"
            ))

            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def delete_candidate(self, candidate_id: str) -> bool:
        """
        Deletes a single candidate and all associated child records from DB,
        and removes generated data from data/processed/{candidate_id}.
        """
        session = self.session_factory()
        try:
            session.query(Education).filter(Education.candidate_id == candidate_id).delete()
            session.query(Employment).filter(Employment.candidate_id == candidate_id).delete()
            session.query(Publication).filter(Publication.candidate_id == candidate_id).delete()
            session.query(RuleResult).filter(RuleResult.candidate_id == candidate_id).delete()
            session.query(AuditLog).filter(AuditLog.candidate_id == candidate_id).delete()
            deleted = session.query(Candidate).filter(Candidate.id == candidate_id).delete()
            session.commit()

            # Clean disk cache
            cand_dir = settings.data_dir / "processed" / candidate_id
            if cand_dir.exists():
                shutil.rmtree(cand_dir, ignore_errors=True)

            return deleted > 0
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting candidate {candidate_id}: {e}")
            return False
        finally:
            session.close()

    def clear_all_candidates(self) -> int:
        """
        Clears all candidates, educations, employments, publications, rule results,
        audit logs, and removes all folders inside data/processed/.
        Does NOT touch original source PDF files.
        """
        session = self.session_factory()
        try:
            session.query(Education).delete()
            session.query(Employment).delete()
            session.query(Publication).delete()
            session.query(RuleResult).delete()
            session.query(AuditLog).delete()
            count = session.query(Candidate).delete()
            session.commit()

            # Clean processed directory
            processed_dir = settings.data_dir / "processed"
            if processed_dir.exists():
                for item in processed_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    elif item.is_file():
                        item.unlink(missing_ok=True)

            # Clean uploads directory if any
            uploads_dir = settings.data_dir / "uploads"
            if uploads_dir.exists():
                for item in uploads_dir.iterdir():
                    if item.is_file():
                        item.unlink(missing_ok=True)

            return count
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing all candidates: {e}")
            return 0
        finally:
            session.close()

    def _candidate_to_dict(self, c: Candidate) -> Dict[str, Any]:
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
            "total_years": c.total_years,
            "publications_count": c.publications_count,
            "eligibility_status": c.eligibility_status,
            "overall_score": c.overall_score,
            "confidence": c.confidence,
            "review_status": c.review_status,
            "review_notes": c.review_notes,
            "reviewer_verdict": c.reviewer_verdict,
            "file_name": c.file_name,
            "file_path": c.file_path,
            "is_uploaded": bool(c.is_uploaded),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "education": [
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
            "publications": [
                {
                    "title": p.title,
                    "venue": p.venue,
                    "year": p.year,
                    "doi": p.doi,
                    "indexed": p.indexed,
                    "evidence": p.evidence
                } for p in c.publications
            ],
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

candidate_repo = CandidateRepository()
