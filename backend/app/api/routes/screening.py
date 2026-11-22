from fastapi import APIRouter, HTTPException
from typing import Literal, Optional
from pydantic import BaseModel
from backend.app.config import config_manager
from backend.app.database.repository import candidate_repo
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.services.screening_service import screening_service
from backend.app.utils.json_utils import atomic_write_text, safe_child_path, validate_candidate_id

router = APIRouter(prefix="/screening", tags=["Screening"])

class ReviewActionPayload(BaseModel):
    verdict: Literal["approved", "eligible", "rejected", "disqualified"]
    notes: Optional[str] = None

@router.get("/review-queue")
def get_review_queue():
    """
    Returns candidates requiring human review with specific flagged reasons.
    """
    queue_candidates = candidate_repo.get_review_queue()
    enriched_queue = []

    review_cfg = config_manager.get_review_config()
    queue_conf = float(review_cfg["queue_confidence_threshold"])
    min_teach = float(review_cfg["queue_min_teaching_years"])

    for c in queue_candidates:
        # Determine why review is required
        flags = []
        if c.get("confidence", 1.0) < queue_conf:
            flags.append(f"Low overall confidence ({int(c.get('confidence', 0)*100)}%)")
        if c.get("highest_institution_category") in ["Other", "Unknown"]:
            flags.append("Institution category ambiguous or unclassified")
        if not c.get("highest_degree") or c.get("highest_degree") == "Other":
            flags.append("Degree level requires manual confirmation")
        if c.get("teaching_years", 0) < min_teach:
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
    try:
        cid = validate_candidate_id(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid candidate ID format: {candidate_id}")

    success = candidate_repo.update_review(cid, verdict=payload.verdict, notes=payload.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "success", "candidate_id": cid, "verdict": payload.verdict}

@router.post("/run")
def trigger_screening_run(preserve_manual_reviews: bool = True):
    """
    Re-evaluates all stored candidates against active screening rules.
    Preserves manual reviewer verdicts by default and writes updated resume.json and resume.md atomically.
    """
    import json
    from backend.app.schemas.resume import ResumeProfile
    from backend.app.utils.markdown_generator import MarkdownGenerator

    screening_service.reload_rules()
    candidate_ids = candidate_repo.list_all_candidate_ids()
    updated = 0
    preserved = 0

    for cand_id in candidate_ids:
        try:
            cid = validate_candidate_id(cand_id)
            p_dir = safe_child_path(orchestrator.processed_dir, cid)
        except ValueError:
            continue

        p_path = p_dir / "resume.json"
        if not p_path.exists():
            continue

        cand = candidate_repo.get_candidate(cid) or {}
        with open(p_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        prof = ResumeProfile(**data)
        prof.screening = screening_service.evaluate_candidate(prof)

        if prof.metadata is not None:
            if prof.metadata.grounding_score is not None and prof.metadata.grounding_score < 0.75:
                if prof.screening.eligibility_status == "eligible":
                    prof.screening.eligibility_status = "needs_review"
                prof.screening.flags.append(
                    f"Source grounding score ({prof.metadata.grounding_score:.2f}) below threshold (0.75); flagged for manual review."
                )
            if prof.metadata.json_repaired:
                if prof.screening.eligibility_status == "eligible":
                    prof.screening.eligibility_status = "needs_review"
                prof.screening.flags.append(
                    "LLM output required heuristic JSON repair; manual verification recommended."
                )

        existing_review_status = cand.get("review_status") or prof.review_status
        existing_verdict = cand.get("reviewer_verdict") or prof.reviewer_verdict
        existing_notes = cand.get("review_notes") if cand.get("review_notes") is not None else prof.review_notes
        if preserve_manual_reviews and existing_review_status in ("Manually verified", "Disqualified") and existing_verdict:
            prof.review_status = existing_review_status
            prof.reviewer_verdict = existing_verdict
            prof.review_notes = existing_notes
            prof.screening.eligibility_status = "eligible" if existing_verdict in ("approved", "eligible") else "disqualified"
            preserved += 1

        candidate_repo.save_profile(prof)

        atomic_write_text(p_path, prof.model_dump_json(indent=2))
        md_content = MarkdownGenerator.generate_markdown(prof)
        atomic_write_text(p_dir / "resume.md", md_content)

        updated += 1

    return {
        "status": "success",
        "updated": updated,
        "preserved_manual_reviews": preserved,
        "message": f"Screening re-run complete for {updated} candidates ({preserved} manual reviews preserved)"
    }
