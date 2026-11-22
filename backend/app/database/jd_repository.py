import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc

from backend.app.agents.evaluation_agent import DynamicEvaluationAgent
from backend.app.config import settings
from backend.app.database.models import AuditLog, Candidate, JDEvaluation, JobDescription, SessionLocal, init_db
from backend.app.database.repository import CandidateRepository
from backend.app.schemas.jd import (
    CandidateJDEvaluation,
    DimensionScores,
    JDWeights,
    JobDescriptionSpec,
    RequirementMatch,
)
from backend.app.schemas.resume import (
    AcademicLink,
    CourseTaughtEntry,
    EducationEntry,
    EmploymentEntry,
    ExperienceBreakdown,
    ExternalVerification,
    NotableHighlight,
    ProcessingMetadata,
    PublicationEntry,
    ResearchProfile,
    ResumeProfile,
    ScreeningResult,
    SourceEvidence,
    SupervisionSummary,
)
from backend.app.utils.json_utils import safe_child_path, validate_candidate_id

logger = logging.getLogger("FacultyScreen.JDRepository")


class JDRepository:
    """Repository for structured Job Descriptions, per-JD dynamic evaluations, and committee approvals."""

    def __init__(self, db_session_factory=SessionLocal):
        self.session_factory = db_session_factory
        self._cand_repo = CandidateRepository(db_session_factory=db_session_factory)
        if db_session_factory is SessionLocal:
            init_db()

    @staticmethod
    def _jd_to_dict(jd: JobDescription, eval_count: int = 0) -> Dict[str, Any]:
        spec = json.loads(jd.parsed_spec_json)
        weights = json.loads(jd.weights_json) if jd.weights_json else spec.get("weights", {})
        spec["weights"] = weights
        return {
            "jd_id": jd.id,
            "title": jd.title,
            "department": jd.department,
            "level": jd.level,
            "role_archetype": jd.role_archetype,
            "raw_text": jd.raw_text,
            "file_name": jd.file_name,
            "is_active": bool(jd.is_active),
            "evaluated_count": eval_count,
            "created_at": jd.created_at.isoformat() if jd.created_at else None,
            "updated_at": jd.updated_at.isoformat() if jd.updated_at else None,
            **spec,
        }

    @staticmethod
    def _eval_to_dict(ev: JDEvaluation) -> Dict[str, Any]:
        return {
            "jd_id": ev.jd_id,
            "candidate_id": ev.candidate_id,
            "dynamic_score": ev.dynamic_score,
            "recommendation_tier": ev.recommendation_tier,
            "confidence": ev.confidence,
            "grounding_score": ev.grounding_score,
            "dimension_scores": json.loads(ev.dimension_scores_json),
            "requirement_matrix": json.loads(ev.requirement_matrix_json),
            "compensating_strengths": json.loads(ev.compensating_strengths_json) if ev.compensating_strengths_json else [],
            "standout_highlights": json.loads(ev.standout_highlights_json) if ev.standout_highlights_json else [],
            "executive_brief": ev.executive_brief or "",
            "interview_probes": json.loads(ev.interview_probes_json) if ev.interview_probes_json else [],
            "approval_status": ev.approval_status or "pending",
            "approval_notes": ev.approval_notes,
            "approved_by": ev.approved_by,
            "approved_at": ev.approved_at.isoformat() if ev.approved_at else None,
            "evaluated_at": ev.evaluated_at.isoformat() if ev.evaluated_at else None,
        }

    def save_jd(
        self,
        spec: JobDescriptionSpec,
        raw_text: str,
        file_name: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        jd_id = validate_candidate_id(spec.jd_id)
        session = self.session_factory()
        try:
            row = session.query(JobDescription).filter(JobDescription.id == jd_id).first()
            if not row:
                row = JobDescription(id=jd_id, raw_text=raw_text, parsed_spec_json="{}")
                session.add(row)
            row.title = spec.title
            row.department = spec.department
            row.level = spec.level
            row.role_archetype = spec.role_archetype
            row.raw_text = raw_text
            if file_name is not None:
                row.file_name = file_name
            if file_path is not None:
                row.file_path = file_path
            row.parsed_spec_json = spec.model_dump_json()
            row.weights_json = spec.weights.model_dump_json()
            row.is_active = True
            session.commit()
            eval_count = session.query(JDEvaluation).filter(JDEvaluation.jd_id == jd_id).count()
            return self._jd_to_dict(row, eval_count=eval_count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_jd(self, jd_id: str) -> Optional[Dict[str, Any]]:
        clean_id = validate_candidate_id(jd_id)
        session = self.session_factory()
        try:
            row = session.query(JobDescription).filter(JobDescription.id == clean_id).first()
            if not row:
                return None
            eval_count = session.query(JDEvaluation).filter(JDEvaluation.jd_id == clean_id).count()
            return self._jd_to_dict(row, eval_count=eval_count)
        finally:
            session.close()

    def get_jd_spec(self, jd_id: str) -> Optional[JobDescriptionSpec]:
        data = self.get_jd(jd_id)
        if not data:
            return None
        return JobDescriptionSpec(**data)

    def list_jds(self) -> List[Dict[str, Any]]:
        session = self.session_factory()
        try:
            rows = session.query(JobDescription).order_by(desc(JobDescription.updated_at)).all()
            out = []
            for row in rows:
                cnt = session.query(JDEvaluation).filter(JDEvaluation.jd_id == row.id).count()
                out.append(self._jd_to_dict(row, eval_count=cnt))
            return out
        finally:
            session.close()

    def update_jd(self, jd_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        clean_id = validate_candidate_id(jd_id)
        session = self.session_factory()
        try:
            row = session.query(JobDescription).filter(JobDescription.id == clean_id).first()
            if not row:
                return None
            spec_data = json.loads(row.parsed_spec_json)
            for key in (
                "title",
                "department",
                "level",
                "role_archetype",
                "summary",
                "requirements",
                "required_domains",
                "preferred_courses",
                "research_expectations",
                "industry_practice_value",
                "allow_compensating_strengths",
                "weights",
            ):
                if key in patch and patch[key] is not None:
                    spec_data[key] = patch[key]

            spec = JobDescriptionSpec(**spec_data)
            row.title = spec.title
            row.department = spec.department
            row.level = spec.level
            row.role_archetype = spec.role_archetype
            row.parsed_spec_json = spec.model_dump_json()
            row.weights_json = spec.weights.model_dump_json()

            # Instantaneously recalculate stored evaluations without re-running LLMs
            evals = session.query(JDEvaluation).filter(JDEvaluation.jd_id == clean_id).all()
            for ev in evals:
                dims = DimensionScores(**json.loads(ev.dimension_scores_json))
                matrix = [RequirementMatch(**m) for m in json.loads(ev.requirement_matrix_json)]
                new_score, new_tier = DynamicEvaluationAgent.recompute_composite_and_tier(
                    dims, spec.weights, matrix, spec.allow_compensating_strengths
                )
                ev.dynamic_score = new_score
                ev.recommendation_tier = new_tier

            session.commit()
            return self._jd_to_dict(row, eval_count=len(evals))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_jd(self, jd_id: str) -> bool:
        clean_id = validate_candidate_id(jd_id)
        session = self.session_factory()
        try:
            session.query(JDEvaluation).filter(JDEvaluation.jd_id == clean_id).delete()
            deleted = session.query(JobDescription).filter(JobDescription.id == clean_id).delete()
            session.commit()
            return deleted > 0
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def save_evaluation(self, evaluation: CandidateJDEvaluation) -> Dict[str, Any]:
        jd_id = validate_candidate_id(evaluation.jd_id)
        cand_id = validate_candidate_id(evaluation.candidate_id)
        session = self.session_factory()
        try:
            row = (
                session.query(JDEvaluation)
                .filter(JDEvaluation.jd_id == jd_id, JDEvaluation.candidate_id == cand_id)
                .first()
            )
            if not row:
                row = JDEvaluation(
                    jd_id=jd_id,
                    candidate_id=cand_id,
                    dimension_scores_json="{}",
                    requirement_matrix_json="[]",
                )
                session.add(row)

            row.dynamic_score = evaluation.dynamic_score
            row.recommendation_tier = evaluation.recommendation_tier
            row.confidence = evaluation.confidence
            row.grounding_score = evaluation.grounding_score
            row.dimension_scores_json = evaluation.dimension_scores.model_dump_json()
            row.requirement_matrix_json = json.dumps([r.model_dump() for r in evaluation.requirement_matrix])
            row.compensating_strengths_json = json.dumps([c.model_dump() for c in evaluation.compensating_strengths])
            row.standout_highlights_json = json.dumps([h.model_dump() for h in evaluation.standout_highlights])
            row.executive_brief = evaluation.executive_brief
            row.interview_probes_json = json.dumps(evaluation.interview_probes)
            row.evaluated_at = datetime.now(timezone.utc)
            session.commit()
            return self._eval_to_dict(row)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_evaluation(self, jd_id: str, candidate_id: str) -> Optional[Dict[str, Any]]:
        clean_jd = validate_candidate_id(jd_id)
        clean_cand = validate_candidate_id(candidate_id)
        session = self.session_factory()
        try:
            row = (
                session.query(JDEvaluation)
                .filter(JDEvaluation.jd_id == clean_jd, JDEvaluation.candidate_id == clean_cand)
                .first()
            )
            return self._eval_to_dict(row) if row else None
        finally:
            session.close()

    def list_evaluations_for_jd(self, jd_id: str) -> List[Dict[str, Any]]:
        clean_jd = validate_candidate_id(jd_id)
        session = self.session_factory()
        try:
            rows = (
                session.query(JDEvaluation)
                .filter(JDEvaluation.jd_id == clean_jd)
                .order_by(desc(JDEvaluation.dynamic_score))
                .all()
            )
            results: List[Dict[str, Any]] = []
            for ev in rows:
                cand_row = session.query(Candidate).filter(Candidate.id == ev.candidate_id).first()
                if not cand_row:
                    continue
                cand_dict = self._cand_repo._candidate_to_dict(cand_row)
                cand_dict["jd_evaluation"] = self._eval_to_dict(ev)
                results.append(cand_dict)
            return results
        finally:
            session.close()

    def update_approval(
        self,
        jd_id: str,
        candidate_id: str,
        approval_status: str,
        notes: Optional[str] = None,
        actor: str = "recruiter",
    ) -> Optional[Dict[str, Any]]:
        clean_jd = validate_candidate_id(jd_id)
        clean_cand = validate_candidate_id(candidate_id)
        session = self.session_factory()
        try:
            row = (
                session.query(JDEvaluation)
                .filter(JDEvaluation.jd_id == clean_jd, JDEvaluation.candidate_id == clean_cand)
                .first()
            )
            if not row:
                return None
            row.approval_status = approval_status
            row.approval_notes = notes
            row.approved_by = actor
            row.approved_at = datetime.now(timezone.utc)

            session.add(
                AuditLog(
                    candidate_id=clean_cand,
                    action="JD_APPROVAL_UPDATED",
                    actor=actor,
                    details=f"JD={clean_jd}, Status={approval_status}, Notes={notes}",
                )
            )
            session.commit()
            return self._eval_to_dict(row)
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()


    def load_profile_for_candidate(self, candidate_id: str) -> Optional[ResumeProfile]:
        clean_id = validate_candidate_id(candidate_id)
        try:
            json_path = safe_child_path(settings.data_dir / "processed", clean_id) / "resume.json"
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    return ResumeProfile(**json.load(f))
        except Exception:
            pass

        cand = self._cand_repo.get_candidate(clean_id)
        if not cand:
            return None

        ext = cand.get("external_verification")
        return ResumeProfile(
            candidate_id=clean_id,
            name=cand.get("name") or "Candidate",
            email=cand.get("email"),
            phone=cand.get("phone"),
            location=cand.get("location"),
            current_designation=cand.get("current_designation"),
            summary=cand.get("summary"),
            education=[EducationEntry(**e) for e in cand.get("education", [])],
            experience=ExperienceBreakdown(
                total_years=float(cand.get("total_years") or 0.0),
                teaching_years=float(cand.get("teaching_years") or 0.0),
                research_years=float(cand.get("research_years") or 0.0),
                industry_years=float(cand.get("industry_years") or 0.0),
                administrative_years=float(cand.get("administrative_years") or 0.0),
            ),
            employment=[EmploymentEntry(**e) for e in cand.get("employment", [])],
            research=ResearchProfile(
                publications=[PublicationEntry(**p) for p in cand.get("publications", [])],
                patents=(cand.get("research") or {}).get("patents", []),
                research_projects=(cand.get("research") or {}).get("research_projects", []),
                research_domains=(cand.get("research") or {}).get("research_domains", []),
                books=(cand.get("research") or {}).get("books", []),
            ),
            certifications=cand.get("certifications", []),
            awards=cand.get("awards", []),
            skills=cand.get("skills", []),
            courses_taught=[CourseTaughtEntry(**c) for c in cand.get("courses_taught", [])],
            teaching_interests=cand.get("teaching_interests", []),
            academic_links=[AcademicLink(**l) for l in cand.get("academic_links", [])],
            supervision=SupervisionSummary(**(cand.get("supervision") or {})),
            academic_service=cand.get("academic_service", []),
            notable_highlights=[NotableHighlight(**h) for h in cand.get("notable_highlights", [])],
            external_verification=ExternalVerification(**ext) if isinstance(ext, dict) else None,
            projects=cand.get("projects", []),
            screening=ScreeningResult(
                eligibility_status=cand.get("eligibility_status") or "needs_review",
                overall_score=float(cand.get("overall_score") or 0.0),
                confidence=float(cand.get("confidence") or 0.9),
                flags=cand.get("screening_flags", []),
                rules_evaluated=[],
                decision_path=cand.get("decision_path", []),
            ),
            source_evidence=[SourceEvidence(**s) for s in cand.get("source_evidence", [])],
            metadata=ProcessingMetadata(**cand["metadata"]) if isinstance(cand.get("metadata"), dict) else None,
        )


jd_repo = JDRepository()
