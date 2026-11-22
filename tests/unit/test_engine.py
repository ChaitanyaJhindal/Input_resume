import pytest
from backend.app.services.institution_service import institution_service
from backend.app.services.education_service import EducationService
from backend.app.services.experience_service import ExperienceService
from backend.app.services.screening_service import screening_service
from backend.app.services.jev.jev_router import jev_router
from backend.app.services.jev.jev_client import JevClient
from backend.app.services.jev.jev_schemas import JevDecisionRequest
from backend.app.schemas.resume import (
    ResumeProfile, EducationEntry, EmploymentEntry, ExperienceBreakdown,
    PublicationEntry, ResearchProfile
)
from backend.app.utils.markdown_generator import MarkdownGenerator

def test_institution_normalization():
    # Test IIT alias
    norm, cat, tier, conf = institution_service.classify_institution("I.I.T. Delhi")
    assert norm == "IIT Delhi"
    assert cat == "IIT"
    assert tier == "Tier 1"
    assert conf >= 0.95

    # Test NIT alias
    norm_nit, cat_nit, tier_nit, conf_nit = institution_service.classify_institution("National Institute of Technology Trichy")
    assert norm_nit == "NIT Trichy"
    assert cat_nit == "NIT"
    assert tier_nit == "Tier 1"

    # Test Central University
    norm_jnu, cat_jnu, tier_jnu, _ = institution_service.classify_institution("Jawaharlal Nehru University")
    assert norm_jnu == "Jawaharlal Nehru University"
    assert cat_jnu == "Central University"

    # Test International University
    norm_mit, cat_mit, tier_mit, _ = institution_service.classify_institution("MIT")
    assert norm_mit == "Massachusetts Institute of Technology"
    assert cat_mit == "International University"
    assert tier_mit == "Tier 1"
    assert cat_mit == "International University"

def test_degree_normalization():
    # Ph.D. variations
    norm, conf = EducationService.normalize_degree("Doctor of Philosophy")
    assert norm == "PhD / Doctorate"
    assert conf >= 0.9

    norm_phd, _ = EducationService.normalize_degree("Ph.D. in Computer Science")
    assert norm_phd == "PhD / Doctorate"

    norm_dphil, _ = EducationService.normalize_degree("D.Phil")
    assert norm_dphil == "PhD / Doctorate"

    # Masters variations
    norm_mtech, _ = EducationService.normalize_degree("M.Tech in Information Technology")
    assert norm_mtech == "Postgraduate / Masters"

    norm_ms, _ = EducationService.normalize_degree("Master of Science")
    assert norm_ms == "Postgraduate / Masters"

    # Undergraduate
    norm_btech, _ = EducationService.normalize_degree("Bachelor of Technology")
    assert norm_btech == "Undergraduate"

    norm_be, _ = EducationService.normalize_degree("B.E. Computer Science")
    assert norm_be == "Undergraduate"

def test_experience_calculation_and_interval_merging():
    entries = [
        EmploymentEntry(
            title="Lecturer",
            organization="College A",
            category="teaching",
            start_date="2018",
            end_date="2021",
            duration_years=3.0
        ),
        EmploymentEntry(
            title="Software Engineer",
            organization="Tech Corp",
            category="industry",
            start_date="2021",
            end_date="2024",
            duration_years=3.0
        ),
        EmploymentEntry(
            title="Assistant Professor",
            organization="University B",
            category="teaching",
            start_date="2024",
            end_date="2026",
            duration_years=2.0
        )
    ]

    breakdown = ExperienceService.calculate_experience(entries)
    # Teaching: 2018-2021 (3 yrs) + 2024-2026 (2 yrs) = 5.0 years
    assert breakdown.teaching_years == 5.0
    # Industry: 2021-2024 = 3.0 years
    assert breakdown.industry_years == 3.0
    # Total non-overlapping: 2018 to 2026 = 8.0 years
    assert breakdown.total_years == 8.0

def test_jev_client_and_router():
    client = JevClient()
    req = JevDecisionRequest(
        task="classify_degree",
        context={"raw_degree": "Ph.D. in Electrical Engineering"},
        candidate_options=["PhD / Doctorate", "Postgraduate / Masters"]
    )
    resp = client.execute_decision(req)
    assert resp.decision == "PhD / Doctorate"
    assert resp.confidence >= 0.85

    # Test Router telemetry tracking
    initial_jev_calls = jev_router.stats["jev_decision_calls"]
    decision, conf, rationale, tier = jev_router.route_decision(
        task="classify_degree",
        context={"raw_degree": "M.Tech in VLSI"}
    )
    assert decision == "Postgraduate / Masters"
    assert jev_router.stats["jev_decision_calls"] == initial_jev_calls + 1

def test_screening_rule_engine():
    profile = ResumeProfile(
        candidate_id="cand_test_01",
        name="Dr. Jane Doe",
        education=[
            EducationEntry(
                degree="Ph.D. in Computer Science",
                normalized_degree="PhD / Doctorate",
                institution="IIT Delhi",
                institution_normalized="IIT Delhi",
                institution_category="IIT",
                institution_tier="Tier 1",
                graduation_year=2020
            )
        ],
        experience=ExperienceBreakdown(
            total_years=6.0,
            teaching_years=3.5,
            research_years=2.5,
            industry_years=0.0
        ),
        research=ResearchProfile(
            publications=[
                PublicationEntry(title="Paper 1", venue="IEEE", year=2022),
                PublicationEntry(title="Paper 2", venue="ACM", year=2023)
            ]
        )
    )

    result = screening_service.evaluate_candidate(profile)
    assert result.eligibility_status == "eligible"
    assert result.overall_score >= 70.0
    assert len(result.rules_evaluated) >= 4

    # Now test candidate who fails mandatory Ph.D. rule
    profile_fail = ResumeProfile(
        candidate_id="cand_test_02",
        name="John Masters",
        education=[
            EducationEntry(
                degree="B.Tech in Computer Science",
                normalized_degree="Undergraduate",
                institution="Local College",
                institution_normalized="Local College",
                institution_category="Private University"
            )
        ],
        experience=ExperienceBreakdown(teaching_years=0.5),
        research=ResearchProfile(publications=[])
    )

    result_fail = screening_service.evaluate_candidate(profile_fail)
    assert result_fail.eligibility_status == "disqualified"
    assert any("Mandatory requirement failed" in flag for flag in result_fail.flags)

def test_markdown_generator():
    profile = ResumeProfile(
        candidate_id="cand_test_03",
        name="Dr. Alan Turing",
        current_designation="Professor of Computing",
        education=[
            EducationEntry(
                degree="Ph.D. in Mathematics",
                normalized_degree="PhD / Doctorate",
                institution="Cambridge University",
                institution_normalized="Cambridge University",
                institution_category="International University",
                evidence="Ph.D. Mathematics, Cambridge"
            )
        ],
        experience=ExperienceBreakdown(
            total_years=10.0,
            teaching_years=8.0,
            research_years=5.0
        ),
        research=ResearchProfile(
            publications=[
                PublicationEntry(
                    title="On Computable Numbers",
                    venue="London Mathematical Society",
                    year=1936
                )
            ]
        )
    )

    md = MarkdownGenerator.generate_markdown(profile)
    assert "# Dr. Alan Turing" in md
    assert "## Education" in md
    assert "Cambridge University" in md
    assert "On Computable Numbers" in md
    assert "Academic Teaching Experience" in md
