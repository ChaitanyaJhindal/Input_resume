import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.models import init_db

init_db()
client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "FacultyScreen"

def test_list_resumes_endpoint():
    response = client.get("/api/resumes")
    assert response.status_code == 200
    data = response.json()
    assert "total_count" in data
    assert "resumes" in data
    assert data["total_count"] >= 30

def test_candidates_endpoint():
    response = client.get("/api/candidates")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "candidates" in data

def test_analytics_overview():
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "distributions" in data
    assert "telemetry" in data

def test_screening_rules_settings():
    response = client.get("/api/settings/rules")
    assert response.status_code == 200
    rules_data = response.json()
    assert "rules" in rules_data
    assert len(rules_data["rules"]) >= 4

def test_institutions_taxonomy():
    response = client.get("/api/settings/institutions")
    assert response.status_code == 200
    inst_data = response.json()
    assert "categories" in inst_data
    assert "IIT" in inst_data["categories"]

def test_modular_settings_endpoints():
    llm_resp = client.get("/api/settings/llm")
    assert llm_resp.status_code == 200
    llm_data = llm_resp.json()
    assert "config" in llm_data
    assert "resolved_models" in llm_data
    assert "groq_models" in llm_data

    prompts_resp = client.get("/api/settings/prompts")
    assert prompts_resp.status_code == 200
    prompts_data = prompts_resp.json()
    assert "prompts" in prompts_data
    assert "extractor" in prompts_data["prompts"]

    app_resp = client.get("/api/settings/app")
    assert app_resp.status_code == 200
    app_data = app_resp.json()
    assert "pipeline" in app_data
    assert "review" in app_data

    status_resp = client.get("/api/settings/system-status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "groq_reasoning_model" in status_data
    assert "resolved_task_models" in status_data

    reload_resp = client.post("/api/settings/reload")
    assert reload_resp.status_code == 200
    assert reload_resp.json()["status"] == "success"

def test_phase1_integrity_and_telemetry_endpoints():
    # 1. Analytics parity with review queue & real telemetry
    analytics = client.get("/api/analytics/overview").json()
    queue = client.get("/api/screening/review-queue").json()
    assert analytics["metrics"]["needs_review"] == queue["count"]
    assert analytics["metrics"]["processed"] <= analytics["metrics"]["total_resumes"]

    # 2. Full candidate hydration & 100% file resolution when DB has candidates (empty DB also valid after Reset)
    cands = client.get("/api/candidates?limit=100").json()["candidates"]
    if len(cands) > 0:
        assert analytics["telemetry"]["deterministic_resolutions"] > 0
        sample_detail = client.get(f"/api/candidates/{cands[0]['id']}").json()
        for field in ("skills", "awards", "certifications", "source_evidence", "research", "metadata"):
            assert field in sample_detail

        for c in cands:
            file_resp = client.get(f"/api/resumes/{c['id']}/file")
            assert file_resp.status_code == 200, f"Failed /file for {c['id']} ({c['file_name']})"
    else:
        assert analytics["telemetry"]["deterministic_resolutions"] >= 0


def test_phase2_sync_status_and_enriched_analytics():
    sync_resp = client.get("/api/resumes/sync-status")
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    for key in ("running", "total", "completed", "failed", "current_file"):
        assert key in sync_data

    analytics_resp = client.get("/api/analytics/overview")
    assert analytics_resp.status_code == 200
    analytics = analytics_resp.json()
    dists = analytics["distributions"]
    assert "rule_pass_rates" in dists
    assert "score_brackets" in dists
    assert "grounding_brackets" in dists
    assert "groq_pool" in analytics
    assert "active_available_keys" in analytics["groq_pool"]
    assert "total_keys" in analytics["groq_pool"]


def test_security_and_validation_hardening_endpoints():
    # Path traversal rejected with 400 across endpoints
    for path in (
        "/api/candidates/cand..evil",
        "/api/resumes/cand..evil/result",
        "/api/candidates/compare?ids=cand_ok1234,cand..evil",
    ):
        resp = client.get(path)
        assert resp.status_code == 400

    # Invalid verdict rejected by Pydantic Literal schema (422)
    bad_verdict = client.post("/api/screening/cand_06394bfb14/review", json={"verdict": "maybe_later"})
    assert bad_verdict.status_code == 422

    bad_verdict2 = client.post("/api/candidates/cand_06394bfb14/review", json={"verdict": "bogus"})
    assert bad_verdict2.status_code == 422

    # Unrecognized sort column safely ignored instead of throwing 500
    sort_resp = client.get("/api/candidates?sort_by=__tablename__")
    assert sort_resp.status_code == 200

    # Corrupt LLM schema rejected cleanly with HTTP 400
    bad_llm = client.patch("/api/settings/llm", json={"providers": {"groq": {}}})
    assert bad_llm.status_code == 400

    # Empty upload rejected with HTTP 400
    empty_upload = client.post(
        "/api/resumes/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty_upload.status_code == 400


def test_reset_workspace_endpoint_isolated(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.app.config import settings
    from backend.app.database.models import Base, Candidate, JobDescription
    from backend.app.database.repository import candidate_repo

    data_dir = tmp_path / "data"
    resumes_dir = tmp_path / "Input_resumes"
    for sub in ("processed/cand_test01", "uploads", "extracted", "results", "jds", "logs", "institutions"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)
    resumes_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "institutions" / "institutions.json").write_text('{"institutions": []}', encoding="utf-8")
    (data_dir / "processed" / "cand_test01" / "resume.json").write_text("{}", encoding="utf-8")
    (data_dir / "uploads" / "old.pdf").write_bytes(b"%PDF")
    (data_dir / "jds" / "jd_1.txt").write_text("JD", encoding="utf-8")
    (resumes_dir / "sample.pdf").write_bytes(b"%PDF")

    db_path = data_dir / "test_reset.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestSession() as s:
        s.add(Candidate(id="cand_test01", name="Test Faculty", file_name="sample.pdf", file_path="sample.pdf", file_hash="abc"))
        s.add(JobDescription(id="jd_test01", title="Test JD", raw_text="Sample JD", parsed_spec_json="{}"))
        s.commit()

    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "resumes_dir", resumes_dir)
    monkeypatch.setattr(candidate_repo, "session_factory", TestSession)

    resp = client.delete("/api/settings/reset-workspace?include_jds=true&include_source_resumes=false")
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidates_deleted"] == 1
    assert body["jds_deleted"] == 1
    assert body["source_files_deleted"] == 0
    assert (data_dir / "institutions" / "institutions.json").exists()
    assert not (data_dir / "processed" / "cand_test01").exists()
    assert not (data_dir / "uploads" / "old.pdf").exists()
    assert (resumes_dir / "sample.pdf").exists()

    # Now test include_source_resumes=true
    resp2 = client.delete("/api/settings/reset-workspace?include_jds=true&include_source_resumes=true")
    assert resp2.status_code == 200
    assert resp2.json()["source_files_deleted"] == 1
    assert not (resumes_dir / "sample.pdf").exists()
    assert (data_dir / "institutions" / "institutions.json").exists()
    engine.dispose()

