from pathlib import Path
from unittest.mock import patch

from backend.app.agents.orchestration_agent import OrchestrationAgent
from backend.app.config import settings
from backend.app.groq.extractor import GroqExtractor
from backend.app.schemas.resume import (
    EducationEntry,
    EmploymentEntry,
    PublicationEntry,
    ResearchProfile,
    ResumeProfile,
)
from backend.app.services.education_service import EducationService
from backend.app.services.experience_service import ExperienceService
from backend.app.services.institution_service import institution_service
from backend.app.services.jev.jev_decisions import JevDecisions
from backend.app.services.validation_service import ValidationService


def test_validation_removes_ungrounded_email_and_flags_hallucinations():
    raw_text = (
        "Dr. Jane Doe\n"
        "Ph.D. in Computer Science, Indian Institute of Technology Delhi, 2020\n"
        "Assistant Professor at Delhi Technological University (2020 - Present)\n"
        "Published: Deep Learning for Academic Document Parsing, IEEE Transactions, 2023\n"
    )
    profile = ResumeProfile(
        candidate_id="cand_val_01",
        name="Dr. Jane Doe",
        email="hallucinated.fake@nowhere.org",
        education=[
            EducationEntry(
                degree="Ph.D. in Computer Science",
                normalized_degree="PhD / Doctorate",
                institution="IIT Delhi",
                graduation_year=2020,
                confidence=0.98,
                evidence="Ph.D. in Computer Science, Indian Institute of Technology Delhi, 2020",
            ),
            EducationEntry(
                degree="Ph.D. in Quantum Astrology",
                normalized_degree="PhD / Doctorate",
                institution="Atlantis Imaginary University",
                graduation_year=2099,
                confidence=0.95,
            ),
        ],
        employment=[
            EmploymentEntry(
                title="Assistant Professor",
                organization="Delhi Technological University",
                category="teaching",
                start_date="2020",
                end_date="Present",
                duration_years=4.0,
            ),
            EmploymentEntry(
                title="Space Admiral",
                organization="Galactic Federation",
                category="industry",
                duration_years=65.0,
            ),
        ],
        research=ResearchProfile(
            publications=[
                PublicationEntry(
                    title="Deep Learning for Academic Document Parsing",
                    venue="IEEE Transactions",
                    year=2023,
                ),
                PublicationEntry(
                    title="Completely Fabricated Paper Title That Never Existed",
                    venue="Fake Journal",
                    year=1812,
                ),
            ]
        ),
    )

    report = ValidationService.validate_and_clean(
        profile, raw_text=raw_text, extraction_meta={"_extraction_method": "groq_text", "_json_repaired": True}
    )

    assert profile.email is None
    assert profile.education[1].graduation_year is None
    assert profile.education[1].confidence <= 0.50
    assert profile.research.publications[1].year is None
    assert report.json_repaired is True
    assert report.grounding_score < 1.0
    assert any("unverified email" in f.lower() for f in report.flags)
    assert any("truncated" in f.lower() for f in report.flags)
    assert any("not grounded" in f.lower() for f in report.flags)


def test_validation_grounded_profile_scores_1_0():
    raw_text = (
        "Dr. Tushar Sharma\n"
        "Email: tushar@iitd.ac.in\n"
        "Ph.D. in Computer Science, IIT Delhi, 2019\n"
        "Assistant Professor, Delhi Technological University, 2019 - Present\n"
        "Publication: Adaptive Rate Control Protocols in Edge Networks, IEEE TKDE, 2022\n"
    )
    profile = ResumeProfile(
        candidate_id="cand_val_02",
        name="Dr. Tushar Sharma",
        email="tushar@iitd.ac.in",
        education=[
            EducationEntry(
                degree="Ph.D. in Computer Science",
                normalized_degree="PhD / Doctorate",
                institution="IIT Delhi",
                graduation_year=2019,
                confidence=0.98,
                evidence="Ph.D. in Computer Science, IIT Delhi, 2019",
            )
        ],
        employment=[
            EmploymentEntry(
                title="Assistant Professor",
                organization="Delhi Technological University",
                category="teaching",
                duration_years=5.0,
            )
        ],
        research=ResearchProfile(
            publications=[
                PublicationEntry(
                    title="Adaptive Rate Control Protocols in Edge Networks",
                    venue="IEEE TKDE",
                    year=2022,
                )
            ]
        ),
    )

    report = ValidationService.validate_and_clean(
        profile, raw_text=raw_text, extraction_meta={"_extraction_method": "groq_text"}
    )
    assert report.grounding_score == 1.0
    assert report.flags == []
    assert profile.email == "tushar@iitd.ac.in"


def test_validation_handles_scanned_pdf_and_failed_extraction():
    profile = ResumeProfile(candidate_id="cand_scan", name="Scanned CV")
    scan_report = ValidationService.validate_and_clean(
        profile, raw_text="", extraction_meta={"_extraction_method": "groq_vision"}
    )
    assert scan_report.grounding_score == 0.80
    assert scan_report.extraction_failed is False
    assert any("vision ocr" in f.lower() for f in scan_report.flags)

    fail_report = ValidationService.validate_and_clean(
        profile, raw_text="some text", extraction_meta={"_extraction_method": "failed", "_extraction_error": "timeout"}
    )
    assert fail_report.extraction_failed is True
    assert fail_report.grounding_score == 0.0
    assert any("failed" in f.lower() for f in fail_report.flags)


def test_live_mode_extraction_failure_never_fabricates_mock_profile(tmp_path: Path):
    dummy_pdf = tmp_path / "test_resume.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%fake\n")

    extractor = GroqExtractor()
    with patch.object(settings, "mock_mode", False):
        with patch("backend.app.groq.extractor.groq_pool") as mock_pool:
            mock_pool.size = 0
            result = extractor.extract_document(dummy_pdf)

    assert result["_extraction_method"] == "failed"
    assert result["email"] is None
    assert result["phone"] is None
    assert result["education"] == []
    assert result["employment"] == []


def test_education_word_boundary_precision_and_ranking():
    assert EducationService.normalize_degree("Bachelor of Pharmacy (B.Pharm)")[0] != "Postgraduate / Masters"
    assert EducationService.normalize_degree("BEng in Computer Science")[0] == "Undergraduate"
    assert EducationService.normalize_degree("BCom in Accounts")[0] == "Undergraduate"
    assert EducationService.normalize_degree("BBM")[0] == "Undergraduate"
    assert EducationService.normalize_degree("Doctor of Business Administration")[0] == "PhD / Doctorate"
    assert EducationService.normalize_degree("PhD Candidate (Expected 2027 - ABD)")[0] == "PhD (In Progress)"
    deg_12, conf_12 = EducationService.normalize_degree("12th")
    assert deg_12 == "Other" and conf_12 >= 0.90

    ordered_highest = EducationService.select_highest_education([
        EducationEntry(degree="12th", normalized_degree="Other", institution="UP Board", graduation_year=2008),
        EducationEntry(degree="B.Tech", normalized_degree="Undergraduate", institution="AKTU", graduation_year=2012),
        EducationEntry(degree="M.Tech", normalized_degree="Postgraduate / Masters", institution="NIT Trichy", graduation_year=2014),
    ])
    assert ordered_highest is not None
    assert ordered_highest.normalized_degree == "Postgraduate / Masters"


def test_institution_classification_accuracy():
    cmu = institution_service.classify_institution("Carnegie Mellon University")
    assert cmu[1] == "International University" and cmu[2] == "Tier 1"

    ubc = institution_service.classify_institution("The University of British Columbia, Canada")
    assert ubc[1] == "International University" and ubc[2] == "Tier 1"

    mnnit = institution_service.classify_institution("MNNIT Allahabad")
    assert mnnit[1] == "NIT" and mnnit[2] == "Tier 1"

    uoa = institution_service.classify_institution("University of Allahabad")
    assert uoa[1] == "Central University"

    bvp = institution_service.classify_institution("Bharti Vidyapeeth, Deemed University")
    assert bvp[1] == "Deemed University"

    unknown = institution_service.classify_institution("Random Horizon University")
    assert unknown[1] == "Other"
    assert unknown[2] == "Unknown / Unclassified"
    assert unknown[3] < 0.85


def test_experience_word_boundaries_and_date_keywords():
    assert ExperienceService.categorize_employment("Methodology Analyst", "Acme Corp", "Research methods") == "industry"
    assert ExperienceService.categorize_employment("Dean of Academics", "State College") == "administrative"
    assert ExperienceService.categorize_employment("Associate Professor & HOD", "IIT Delhi") == "teaching"
    assert ExperienceService.parse_date_decimal("Updated Date: 2021") == 2021.0


def test_jev_resolve_degree_level_tuple_bug_fixed():
    deg, conf = JevDecisions.resolve_degree_level("Mystery Credential XYZ")
    assert deg == "Other"
    assert conf < 0.85


def test_content_hash_candidate_id_deduplicates_filenames(tmp_path: Path):
    f1 = tmp_path / "Resume_A.pdf"
    f2 = tmp_path / "Resume_A_copy.pdf"
    payload = b"%PDF-1.4 identical content bytes"
    f1.write_bytes(payload)
    f2.write_bytes(payload)

    assert OrchestrationAgent.generate_candidate_id(f1) == OrchestrationAgent.generate_candidate_id(f2)
