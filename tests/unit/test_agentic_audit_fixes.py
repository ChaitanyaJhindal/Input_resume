import logging
import shutil
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app.agents.education_agent import EducationAgent
from backend.app.agents.experience_agent import ExperienceAgent
from backend.app.agents.institution_agent import InstitutionAgent
from backend.app.agents.orchestration_agent import OrchestrationAgent
from backend.app.config import config_manager, settings
from backend.app.config_manager import ConfigManager
from backend.app.groq.pool import GroqKeyPool
from backend.app.schemas.resume import (
    EmploymentEntry,
    ResumeProfile,
)
from backend.app.services.experience_service import ExperienceService
from backend.app.services.jev.jev_client import JevClient
from backend.app.services.jev.jev_router import jev_router
from backend.app.services.jev.jev_schemas import JevDecisionRequest
from backend.app.services.research_service import ResearchService
from backend.app.services.validation_service import ValidationService
from backend.app.utils.json_utils import (
    parse_llm_json,
    safe_child_path,
    sanitize_filename,
    validate_candidate_id,
)


def test_lifo_string_aware_json_repair():
    # Braces/brackets inside string literals + deeply nested mid-string truncation
    truncated = (
        '{"name": "Dr. {Bracket} Tester", "education": [{"degree": "PhD [CS]", '
        '"institution": "IIT Delhi", "evidence": "PhD } here"}, {"degree": "M.Tech'
    )
    parsed, repaired = parse_llm_json(truncated)
    assert repaired is True
    assert isinstance(parsed, dict)
    assert parsed["name"] == "Dr. {Bracket} Tester"
    assert len(parsed["education"]) == 2
    assert parsed["education"][0]["institution"] == "IIT Delhi"
    assert parsed["education"][1]["degree"] == "M.Tech"

    # Mid-key truncation must backtrack and still close LIFO order cleanly
    truncated_mid_key = '{"name": "Dr. Backtrack", "education": [{"degree": "PhD", "institution": "NIT'
    parsed2, repaired2 = parse_llm_json(truncated_mid_key + '", "grad')
    assert repaired2 is True
    assert parsed2["education"][0]["institution"] == "NIT"

    # Array output must not be accepted as a dict
    arr_parsed, _ = parse_llm_json('["item1", "item2"]')
    assert arr_parsed is None


def test_path_traversal_and_filename_sanitization(tmp_path: Path):
    assert validate_candidate_id("cand_0123abcd") == "cand_0123abcd"
    for bad in ("../config", "cand/../../etc", "cand_123\x00", "", "ab"):
        with pytest.raises(ValueError):
            validate_candidate_id(bad)

    with pytest.raises(ValueError):
        safe_child_path(tmp_path, "../escape")

    safe_child = safe_child_path(tmp_path, "cand_safe01")
    assert safe_child.parent == tmp_path.resolve()

    assert sanitize_filename("../../evil/..\\cv:name?.pdf") == "cv_name_.pdf"


def test_research_indexing_no_false_positive_on_science():
    assert ResearchService.detect_indexing("Journal of Computer Science") == "Peer-Reviewed"
    assert ResearchService.detect_indexing("Proceedings of Basic Sciences, 2023") == "Peer-Reviewed"
    assert "SCI / SCIE" in ResearchService.detect_indexing("IEEE Sensors Journal (SCIE indexed)")
    assert "Scopus" in ResearchService.detect_indexing("Scopus Indexed Conference")

    res_prof = ResearchService.process_research_profile(
        {
            "publications": [
                {"title": "Graph Learning in Education", "year": "2022"},
                {"title": "Graph Learning in Education!", "year": "2022"},
                "Standalone Paper Title",
            ],
            "patents": ["Patent A"],
            "research_domains": [{"name": "AI"}, "Distributed Systems"],
        }
    )
    assert len(res_prof.publications) == 2
    assert res_prof.patents == [{"title": "Patent A"}]
    assert res_prof.research_domains == ["AI", "Distributed Systems"]


def test_experience_numeric_dates_is_current_and_industry_keywords():
    assert ExperienceService.parse_date_decimal("06/2020") == pytest.approx(2020.42, abs=0.02)
    assert ExperienceService.parse_date_decimal("2021-07") == pytest.approx(2021.50, abs=0.02)
    assert ExperienceService.parse_date_decimal("May-18") == pytest.approx(2018.33, abs=0.02)

    start_d, end_d, dur = ExperienceService.parse_date_range("2021", "", is_current=True)
    assert start_d == 2021.0
    assert end_d > 2025.0
    assert dur >= 4.0

    cat, conf = ExperienceService.categorize_employment_with_confidence(
        "Director of Engineering", "Acme Cloud Systems", "Scaled distributed SaaS microservices"
    )
    assert cat == "industry"
    assert conf >= 0.85

    cat_adm, conf_adm = ExperienceService.categorize_employment_with_confidence(
        "Director of Academics", "State Technical University", "Academic governance"
    )
    assert cat_adm == "administrative"
    assert conf_adm >= 0.85


def test_jev_fallback_eliminates_stale_substring_bugs():
    client = JevClient(api_key="")
    # "Master of Systems" -> "Systems", wait: test "Bachelor of Science in Pharmacy" has "ms" or "be"? "M.Sc in Chemistry" vs "Cyber Systems"
    deg_resp = client.execute_decision(
        JevDecisionRequest(task="classify_degree", context={"raw_degree": "Cyber Systems Certificate"})
    )
    assert deg_resp.decision == "Certification"

    # Unclassified institution must return Other with low confidence and is_escalated=True
    inst_resp = client.execute_decision(
        JevDecisionRequest(
            task="classify_institution",
            context={"institution_name": "Unknown Horizon University"},
            confidence_threshold=0.85,
        )
    )
    assert inst_resp.decision == "Other"
    assert inst_resp.confidence < 0.85
    assert inst_resp.is_escalated is True


def test_unified_agents_jev_telemetry_and_enum_validation():
    before = jev_router.get_telemetry()
    edu_agent = EducationAgent()
    inst_agent = InstitutionAgent()
    exp_agent = ExperienceAgent()

    with patch.object(settings, "mock_mode", False):
        fake_completion_edu = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='```json\n{"normalized_degree": "BogusHallucinatedLevel", "confidence": 1.7}\n```'))]
        )
        fake_completion_inst = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"canonical_name": "Horizon Inst", "category": "InvalidCat", "tier": "Tier X", "confidence": 0.9}'))]
        )
        with patch("backend.app.agents.education_agent.groq_pool") as edu_pool, patch(
            "backend.app.agents.institution_agent.groq_pool"
        ) as inst_pool:
            edu_pool.size = 1
            edu_pool.execute_completion.return_value = fake_completion_edu
            inst_pool.size = 1
            inst_pool.execute_completion.return_value = fake_completion_inst

            norm_deg, deg_conf, deg_src = edu_agent.normalize_detailed("Unusual Foreign Credential")
            assert norm_deg == "Other"
            assert deg_conf <= 1.0
            assert deg_src == "groq_escalation"

            canon, cat, tier, inst_conf, inst_src = inst_agent.classify_detailed("Unusual Horizon Academy")
            assert canon == "Horizon Inst"
            assert cat == "Other"
            assert tier == "Unknown / Unclassified"
            assert inst_src == "groq_escalation"

    # Deterministic corporate SWE role should NOT escalate to LLM
    entries = [
        EmploymentEntry(
            title="Senior Software Engineer",
            organization="Tech Corp",
            category="other",
            start_date="2020",
            end_date="2023",
            duration_years=3.0,
        )
    ]
    breakdown, exp_tele = exp_agent.process_experience_with_meta(entries)
    assert breakdown.industry_years == 3.0
    assert exp_tele["deterministic_resolutions"] == 1
    assert exp_tele["groq_api_calls"] == 0

    after = jev_router.get_telemetry()
    assert after["jev_decision_calls"] >= before["jev_decision_calls"] + 2
    assert after["groq_api_calls"] >= before["groq_api_calls"] + 2


def test_orchestration_agent_handles_malformed_llm_types(tmp_path: Path):
    pdf_file = tmp_path / "malformed_test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nDr. Alice Tester\nPh.D. in Physics, IIT Bombay 2020\n" + b" " * 120)

    malformed_raw = {
        "name": "Dr. Alice Tester",
        "email": None,
        "education": [
            {
                "degree": "Ph.D. in Physics",
                "institution": "IIT Bombay",
                "graduation_year": "2020",
                "source_page": "page 1",
                "evidence": "Ph.D. in Physics, IIT Bombay 2020",
            },
            "Diploma in Data Analytics",
        ],
        "employment": [
            {
                "title": "Assistant Professor",
                "organization": "IIT Bombay",
                "category": "teaching",
                "start_date": "2020",
                "end_date": "",
                "is_current": True,
                "duration_years": "3.5 years",
            }
        ],
        "research": None,
        "skills": None,
        "awards": [{"name": "Best Paper"}],
        "certifications": None,
        "projects": ["Curriculum Portal"],
        "source_evidence": None,
        "_raw_text": "Dr. Alice Tester Ph.D. in Physics IIT Bombay 2020 Assistant Professor IIT Bombay",
        "_page_count": "2 pages",
        "_extraction_method": "groq_text",
        "_model_used": "openai/gpt-oss-20b",
        "_groq_calls": 1,
        "_json_repaired": False,
    }

    agent = OrchestrationAgent(data_dir=tmp_path)
    with patch("backend.app.agents.orchestration_agent.groq_extractor.extract_document", return_value=malformed_raw):
        prof = agent.process_document(pdf_file, force_reprocess=True)

    assert prof.metadata is not None
    assert prof.metadata.model_name == "openai/gpt-oss-20b"
    assert prof.metadata.page_count == 2
    assert prof.awards == ["Best Paper"]
    assert prof.projects == [{"title": "Curriculum Portal"}]
    assert prof.education[0].graduation_year == 2020
    assert prof.experience.teaching_years >= 4.0


def test_validation_empty_extraction_and_deduplication():
    raw_text = "Dr. Bob Candidate " + ("Academic details line with enough content for text layer. " * 4)
    profile = ResumeProfile(
        candidate_id="cand_empty_extr",
        name="Dr. Bob Candidate",
        employment=[
            EmploymentEntry(title="Lecturer", organization="MIT", category="teaching", duration_years=-2.0),
            EmploymentEntry(title="Lecturer", organization="MIT", category="teaching", duration_years=-2.0),
        ],
    )
    report = ValidationService.validate_and_clean(
        profile, raw_text=raw_text, extraction_meta={"_extraction_method": "groq_text"}
    )
    assert report.employment_modified is True
    assert len(profile.employment) == 1
    assert profile.employment[0].duration_years == 0.0

    # Zero extractable claims from text-rich PDF -> grounding_score = 0.50
    empty_profile = ResumeProfile(candidate_id="cand_zero_claims", name="Dr. Zero")
    empty_report = ValidationService.validate_and_clean(
        empty_profile, raw_text=raw_text, extraction_meta={"_extraction_method": "groq_text"}
    )
    assert empty_report.grounding_score == 0.50
    assert any("zero verifiable claims" in f.lower() for f in empty_report.flags)


def test_groq_pool_retries_transient_error_and_does_not_log_key_prefix(caplog):
    pool = GroqKeyPool(keys=["gsk_super_secret_test_key_123456"])
    calls = {"n": 0}

    def flaky_create(**_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("Request timed out transiently")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))])

    pool.key_states[0].client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=flaky_create))
    )

    with caplog.at_level(logging.WARNING), patch("backend.app.groq.pool.time.sleep"):
        pool.key_states[0].mark_rate_limited(duration_sec=1.0)
        pool.key_states[0].cooldown_until = 0.0
        res = pool.execute_completion(model="openai/gpt-oss-20b", messages=[{"role": "user", "content": "hi"}], max_retries=3)

    assert res.choices[0].message.content == '{"ok": true}'
    assert calls["n"] == 2
    assert "gsk_super" not in caplog.text


def test_config_manager_schema_validation(tmp_path: Path):
    for name in ("app_config.yaml", "llm_config.yaml", "prompts.yaml"):
        shutil.copy(settings.config_dir / name, tmp_path / name)

    mgr = ConfigManager(tmp_path, settings)
    with pytest.raises(ValueError, match="expected top-level 'groq'"):
        mgr.update_llm_config({"providers": {"groq": {"models": {}}}})

    with pytest.raises(ValueError, match="must be a string"):
        mgr.update_prompts({"extractor": {"text_system": 123}})

    with pytest.raises(ValueError, match="at least one of"):
        mgr.update_app_config({"unrelated": {}})
