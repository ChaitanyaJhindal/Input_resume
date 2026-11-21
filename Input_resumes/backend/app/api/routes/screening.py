from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from backend.app.repositories.candidate_repo import candidate_repo
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.services.screening_service import screening_service

router = APIRouter(prefix="/screening", tags=["Screening"])

class ReviewActionPayload(BaseModel):
    verdict: str  # approved, rejected
    notes: Optional[str] = None

@router.get("/review-queue")
def get_review_queue():
    """
    Returns candidates requiring human review with specific flagged reasons.
    """
    queue_candidates = candidate_repo.get_review_queue()
    enriched_queue = []

    for c in queue_candidates:
        # Determine why review is required
        flags = []
        if c.get("confidence", 1.0) < 0.85:
            flags.append(f"Low overall confidence ({int(c.get('confidence', 0)*100)}%)")
        if c.get("highest_institution_category") in ["Other", "Unknown"]:
            flags.append("Institution category ambiguous or unclassified")
        if not c.get("highest_degree") or c.get("highest_degree") == "Other":
            flags.append("Degree level requires manual confirmation")
        if c.get("teaching_years", 0) < 2.0:
            flags.append("Teaching experience under standard mandatory threshold")

        for r in c.get("rules_evaluated", []):
            if r.get("status") == "fail" and r.get("is_mandatory"):
                flags.append(f"Failed mandatory rule: {r.get('name')}")

        enriched_queue.append({
            **c,
            "review_reasons": flags if flags else ["Requires routine spot-check audit"]
        })

    return {
        "count": len(enriched_queue),
        "queue": enriched_queue
    }

@router.post("/{candidate_id}/review")
def review_candidate(candidate_id: str, payload: ReviewActionPayload):
    """
    Approve or reject a candidate in the human review queue.
    """
    success = candidate_repo.update_review(candidate_id, verdict=payload.verdict, notes=payload.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "success", "candidate_id": candidate_id, "verdict": payload.verdict}

@router.post("/run")
def trigger_screening_run():
    """
    Re-evaluates all stored candidates against active screening rules.
    """
    screening_service.reload_rules()
    candidates, _ = candidate_repo.list_candidates(limit=1000)
    updated = 0

    for cand in candidates:
        cand_id = cand["id"]
        # Reload full profile from disk if available
        import json
        p_path = orchestrator.processed_dir / cand_id / "resume.json"
        if p_path.exists():
            with open(p_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            from backend.app.schemas.resume import ResumeProfile
            prof = ResumeProfile(**data)
            prof.screening = screening_service.evaluate_candidate(prof)
            candidate_repo.save_profile(prof)
            updated += 1

    return {"message": f"Screening re-run complete for {updated} candidates"}
