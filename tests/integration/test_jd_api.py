from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)


def test_jd_lifecycle_evaluation_and_cleanup():
    sample_jd_text = (
        "Assistant Professor - Computer Science & Distributed Systems\n"
        "Department of Computer Science\n"
        "Requirements:\n"
        "- Must hold a Ph.D. in Computer Science or equivalent applied research leadership.\n"
        "- Must have at least 2 years of university teaching experience.\n"
        "- Strong expertise in Machine Learning, Cloud Computing, and Systems.\n"
    )

    with patch.object(settings, "mock_mode", True):
        create_resp = client.post(
            "/api/jds/upload",
            data={
                "raw_text": sample_jd_text,
                "title": "Test JD - Systems Faculty",
                "department": "Computer Science",
            },
        )
        assert create_resp.status_code == 200
        jd = create_resp.json()["jd"]
        jd_id = jd["jd_id"]

        temp_cid = None
        try:
            # List JDs
            list_resp = client.get("/api/jds")
            assert list_resp.status_code == 200
            assert any(item["jd_id"] == jd_id for item in list_resp.json()["jds"])

            # Fetch existing candidate or upload a temporary mock resume if DB was cleared
            cands = client.get("/api/candidates?limit=2").json()["candidates"]
            if not cands:
                import io
                from PIL import Image

                buf = io.BytesIO()
                Image.new("RGB", (24, 24), color=(255, 255, 255)).save(buf, format="PNG")
                up = client.post(
                    "/api/resumes/upload",
                    files={"file": ("jd_test_candidate.png", buf.getvalue(), "image/png")},
                )
                assert up.status_code == 200
                temp_cid = up.json()["candidate_id"]
                cid = temp_cid
            else:
                cid = cands[0]["id"]

            # Sync evaluate 1 candidate
            eval_resp = client.post(
                f"/api/jds/{jd_id}/evaluate",
                json={"candidate_ids": [cid], "all_candidates": False},
            )
            assert eval_resp.status_code == 200
            assert eval_resp.json()["evaluated_count"] == 1

            # Candidates for JD endpoint
            jd_cands = client.get(f"/api/jds/{jd_id}/candidates")
            assert jd_cands.status_code == 200
            assert jd_cands.json()["summary"]["total_evaluated"] == 1

            # Candidate detail with ?jd_id=
            det = client.get(f"/api/candidates/{cid}?jd_id={jd_id}")
            assert det.status_code == 200
            assert det.json().get("jd_evaluation") is not None

            # Update weights instantaneously
            patch_resp = client.patch(
                f"/api/jds/{jd_id}",
                json={
                    "weights": {
                        "requirement_fit": 0.40,
                        "domain_semantic_fit": 0.25,
                        "teaching_fit": 0.15,
                        "research_and_impact": 0.10,
                        "alternative_strength_credit": 0.10,
                    }
                },
            )
            assert patch_resp.status_code == 200

            # Invalid approval enum must return 422
            bad_app = client.post(
                f"/api/jds/{jd_id}/candidates/{cid}/approval",
                json={"approval_status": "invalid_status"},
            )
            assert bad_app.status_code == 422

            # Valid per-JD approval
            ok_app = client.post(
                f"/api/jds/{jd_id}/candidates/{cid}/approval",
                json={"approval_status": "approved_alternative", "notes": "Verified committee test"},
            )
            assert ok_app.status_code == 200
            assert ok_app.json()["evaluation"]["approval_status"] == "approved_alternative"
        finally:
            # Clean up test JD (and temp candidate if uploaded) so real database stays pristine
            if temp_cid:
                client.delete(f"/api/candidates/{temp_cid}")
            del_resp = client.delete(f"/api/jds/{jd_id}")
            assert del_resp.status_code == 200
