import zipfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.agents.evaluation_agent import DynamicEvaluationAgent
from backend.app.agents.jd_agent import JDIntelligenceAgent
from backend.app.config import settings
from backend.app.database.jd_repository import JDRepository
from backend.app.database.models import Base
from backend.app.database.repository import CandidateRepository
from backend.app.schemas.jd import JDRequirement, JDWeights, JobDescriptionSpec
from backend.app.schemas.resume import (
    CourseTaughtEntry,
    EducationEntry,
    EmploymentEntry,
    ExperienceBreakdown,
    PublicationEntry,
    ResearchProfile,
    ResumeProfile,
)


def test_jd_docx_text_extraction_and_deterministic_parse(tmp_path: Path):
    docx_path = tmp_path / "faculty_jd.docx"
    xml_doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Professor of Practice - Distributed AI Systems</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Must have Ph.D. in Computer Science or equivalent extensive industry leadership.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Must have at least 5 years of teaching or applied engineering experience.</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("word/document.xml", xml_doc)

    extracted = JDIntelligenceAgent.extract_text_from_file(docx_path)
    assert "Distributed AI Systems" in extracted
    assert "equivalent extensive industry leadership" in extracted

    with patch.object(settings, "mock_mode", True):
        spec = JDIntelligenceAgent().parse_jd(extracted)
    assert spec.jd_id.startswith("jd_")
    assert len(spec.requirements) >= 1


def test_compensating_strength_vs_strict_mode_and_jd_repo(tmp_path: Path):
    db_path = tmp_path / "jd_test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    cand_repo = CandidateRepository(db_session_factory=session_factory)
    jd_repo = JDRepository(db_session_factory=session_factory)

    # Strong non-PhD industry/applied candidate with courses taught & patents
    alt_candidate = ResumeProfile(
        candidate_id="cand_alt_fit",
        name="Aarav Industry Leader",
        current_designation="Principal ML Architect",
        education=[
            EducationEntry(
                degree="M.Tech in Computer Science",
                normalized_degree="Postgraduate / Masters",
                institution="IIT Bombay",
                institution_normalized="IIT Bombay",
                institution_category="IIT",
                institution_tier="Tier 1",
                graduation_year=2014,
            )
        ],
        employment=[
            EmploymentEntry(
                title="Principal ML Architect",
                organization="CloudAI Labs",
                category="industry",
                start_date="2016",
                end_date="Present",
                duration_years=9.0,
                is_current=True,
            ),
            EmploymentEntry(
                title="Visiting Faculty",
                organization="IIIT Hyderabad",
                category="teaching",
                start_date="2022",
                end_date="Present",
                duration_years=3.0,
                is_current=True,
            ),
        ],
        experience=ExperienceBreakdown(
            total_years=9.0,
            teaching_years=3.0,
            research_years=1.0,
            industry_years=9.0,
            administrative_years=2.0,
        ),
        courses_taught=[
            CourseTaughtEntry(course_name="Distributed Systems", level="PG", institution="IIIT Hyderabad")
        ],
        research=ResearchProfile(
            publications=[PublicationEntry(title="Production ML Scaling", venue="IEEE", year=2023)],
            patents=[{"title": "Distributed Inference Scheduler", "status": "Granted"}],
            research_domains=["Distributed Systems", "Applied ML"],
        ),
        awards=["National Engineering Excellence Award"],
        skills=["Distributed Systems", "MLOps", "PyTorch", "Curriculum Design"],
    )
    cand_repo.save_profile(alt_candidate)

    flexible_jd = JobDescriptionSpec(
        jd_id="jd_flex_ai",
        title="Professor of Practice - Distributed Systems",
        requirements=[
            JDRequirement(
                id="REQ_PHD",
                category="qualification",
                label="Ph.D. in Computer Science or equivalent excellence",
                priority="must_have",
                weight=35,
                strictness="flexible_with_equivalence",
            ),
            JDRequirement(
                id="REQ_TEACH",
                category="teaching",
                label="2 years teaching experience",
                priority="strong_preference",
                weight=25,
                strictness="flexible_with_equivalence",
            ),
            JDRequirement(
                id="REQ_DOMAIN",
                category="domain_skill",
                label="Distributed Systems and MLOps",
                priority="must_have",
                weight=40,
                strictness="flexible_with_equivalence",
            ),
        ],
        required_domains=["Distributed Systems", "MLOps"],
        allow_compensating_strengths=True,
        weights=JDWeights(),
    )
    jd_repo.save_jd(flexible_jd, raw_text="Professor of Practice JD text...")

    evaluator = DynamicEvaluationAgent()
    with patch.object(settings, "mock_mode", True):
        ev = evaluator.evaluate_candidate_against_jd(flexible_jd, alt_candidate)

    assert any(r.status == "compensated" for r in ev.requirement_matrix)
    assert len(ev.compensating_strengths) >= 1
    assert ev.recommendation_tier == "strong_alternative_fit"
    assert ev.dynamic_score >= 65.0

    jd_repo.save_evaluation(ev)

    # Instant weight recalculation via update_jd (without LLM re-run)
    updated_jd = jd_repo.update_jd(
        "jd_flex_ai",
        {
            "allow_compensating_strengths": False,
            "weights": {
                "requirement_fit": 0.60,
                "domain_semantic_fit": 0.15,
                "teaching_fit": 0.10,
                "research_and_impact": 0.15,
                "alternative_strength_credit": 0.0,
            },
        },
    )
    assert updated_jd is not None
    reloaded_eval = jd_repo.get_evaluation("jd_flex_ai", "cand_alt_fit")
    assert reloaded_eval is not None
    assert reloaded_eval["recommendation_tier"] != "strong_alternative_fit"

    # Per-JD approval update persists cleanly
    approved = jd_repo.update_approval(
        "jd_flex_ai", "cand_alt_fit", approval_status="approved_alternative", notes="Strong practical fit"
    )
    assert approved is not None
    assert approved["approval_status"] == "approved_alternative"
    assert approved["approval_notes"] == "Strong practical fit"
