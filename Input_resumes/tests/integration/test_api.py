import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.db_models import init_db

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
