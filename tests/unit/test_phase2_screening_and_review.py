import json
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.models import Base
from backend.app.database.repository import CandidateRepository
from backend.app.schemas.resume import (
    EducationEntry,
    EmploymentEntry,
    ExperienceBreakdown,
    ProcessingMetadata,
    PublicationEntry,
    ResearchProfile,
    ResumeProfile,
    ScreeningResult,
)
from backend.app.services.screening_service import ScreeningService


def _make_profile(candidate_id: str = "cand_test_01", with_roles: bool = True) -> ResumeProfile:
    employment = []
    if with_roles:
        employment = [
            EmploymentEntry(
                title="Assistant Professor",
                organization="IIT Delhi",
                category="teaching",
                duration_years=4.0,
            ),
            EmploymentEntry(
                title="Dean of Academics",
                organization="IIT Delhi",
                category="administrative",
                duration_years=2.0,
            ),
        ]
    return ResumeProfile(
        candidate_id=candidate_id,
        name="Dr. Test Candidate",
        education=[
            EducationEntry(
                degree="Ph.D. in Computer Science",
                normalized_degree="PhD",
                institution="IIT Delhi",
                institution_normalized="IIT Delhi",
                institution_category="IIT",
                institution_tier="Tier 1",
                confidence=0.95,
            )
        ],
        employment=employment,
        experience=ExperienceBreakdown(
            teaching_years=4.0 if with_roles else 0.0,
            research_years=1.0 if with_roles else 0.0,
            industry_years=0.0,
            administrative_years=2.0 if with_roles else 0.0,
            total_years=7.0 if with_roles else 0.0,
        ),
        research=ResearchProfile(
            publications=[PublicationEntry(title="Robust Faculty Screening")] if with_roles else []
        ),
        metadata=ProcessingMetadata(
            file_name="test_cv.pdf",
            file_path="Input_resumes/test_cv.pdf",
            file_hash="deadbeef" * 8,
            processed_at="2026-01-01T00:00:00Z",
        ),
    )


def test_screening_operators_and_fields(tmp_path: Path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        """
rules:
  - id: R_TIER
    name: Tier 1 Only
    field: education.institution_tier
    operator: "!="
    required_value: Tier 3
    is_mandatory: true
    weight: 20
    failure_message: Institution tier too low
  - id: R_TOTAL
    name: Minimum Total Experience
    field: experience.total_years
    operator: ">"
    required_value: 5
    is_mandatory: false
    weight: 20
    failure_message: Requires over 5 total years
  - id: R_ADMIN
    name: Admin Cap
    field: experience.administrative_years
    operator: "<"
    required_value: 5
    is_mandatory: false
    weight: 20
  - id: R_NOT_IN
    name: Exclude Unclassified Degree
    field: education.highest_degree
    operator: not_in
    required_value: [None, Other]
    is_mandatory: true
    weight: 20
  - id: R_REGEX
    name: Regex Tier Match
    field: education.institution_tier
    operator: regex
    required_value: "^tier\\\\s*1$"
    is_mandatory: false
    weight: 10
  - id: R_CONTAINS
    name: Category Contains IIT
    field: education.highest_institution_category
    operator: contains
    required_value: "iit"
    is_mandatory: false
    weight: 10
settings:
  overall_passing_score_percentage: 70.0
  minimum_confidence_for_auto_approval: 0.85
  needs_review_confidence_floor: 0.65
""",
        encoding="utf-8",
    )

    svc = ScreeningService(config_path=rules_file)
    prof = _make_profile()
    res = svc.evaluate_candidate(prof)
    assert res.eligibility_status == "eligible"
    assert res.overall_score == 100.0
    assert all(ev.status == "pass" for ev in res.rules_evaluated)

    # Check failure_message inclusion + dynamic lower confidence when employment is empty
    empty_prof = _make_profile("cand_empty", with_roles=False)
    res_fail = svc.evaluate_candidate(empty_prof)
    total_rule = next(ev for ev in res_fail.rules_evaluated if ev.rule_id == "R_TOTAL")
    assert total_rule.status == "fail"
    assert "Requires over 5 total years" in total_rule.reason
    assert total_rule.confidence == pytest.approx(0.70)

    # Invalid regex must fail gracefully rather than raising
    passed, msg = svc._evaluate_condition("Tier 1", "regex", "[invalid(")
    assert passed is False
    assert "Invalid regex" in msg


def test_review_queue_excludes_manually_reviewed_and_syncs_disk(tmp_path: Path, monkeypatch):
    from backend.app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    processed_dir = tmp_path / "processed" / "cand_low_conf"
    processed_dir.mkdir(parents=True, exist_ok=True)

    db_path = tmp_path / "test_facultyscreen.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    repo = CandidateRepository(db_session_factory=session_factory)

    profile = _make_profile("cand_low_conf", with_roles=True)
    profile.screening = ScreeningResult(
        eligibility_status="needs_review",
        overall_score=80.0,
        confidence=0.40,
        flags=["Low confidence check"],
        rules_evaluated=[],
        decision_path=[],
    )
    (processed_dir / "resume.json").write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    repo.save_profile(profile)

    queue_before = repo.get_review_queue()
    assert any(item["id"] == "cand_low_conf" for item in queue_before)

    ok = repo.update_review("cand_low_conf", verdict="approved", notes="Verified transcripts")
    assert ok is True

    # Low confidence must NOT re-enter review queue after manual verification
    queue_after = repo.get_review_queue()
    assert all(item["id"] != "cand_low_conf" for item in queue_after)

    saved_disk = json.loads((processed_dir / "resume.json").read_text(encoding="utf-8"))
    assert saved_disk["review_status"] == "Manually verified"
    assert saved_disk["reviewer_verdict"] == "approved"
    assert saved_disk["screening"]["eligibility_status"] == "eligible"
    assert (processed_dir / "resume.md").exists()
    assert "ELIGIBLE" in (processed_dir / "resume.md").read_text(encoding="utf-8")
