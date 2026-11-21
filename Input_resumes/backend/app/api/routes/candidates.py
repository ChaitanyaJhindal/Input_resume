from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.repositories.candidate_repo import candidate_repo
from backend.app.pipelines.orchestrator import orchestrator

router = APIRouter(prefix="/candidates", tags=["Candidates"])

class ReviewSubmission(BaseModel):
    verdict: str  # approved, eligible, rejected, disqualified
    notes: Optional[str] = None

@router.get("")
def list_candidates(
    search: Optional[str] = None,
    degree: Optional[str] = None,
    institution_category: Optional[str] = None,
    min_teaching_years: Optional[float] = None,
    eligibility_status: Optional[str] = None,
    review_status: Optional[str] = None,
    uploaded_only: bool = False,
    sort_by: str = "overall_score",
    sort_desc: bool = True,
    limit: int = 50,
    offset: int = 0
):
    """
    Search and filter candidates with sorting and pagination.
    """
    candidates, total = candidate_repo.list_candidates(
        search=search,
        degree=degree,
        institution_category=institution_category,
        min_teaching_years=min_teaching_years,
        eligibility_status=eligibility_status,
        review_status=review_status,
        uploaded_only=uploaded_only,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "candidates": candidates
    }

@router.get("/compare")
def compare_candidates(ids: str = Query(..., description="Comma-separated candidate IDs (2 to 4 candidates)")):
    """
    Returns side-by-side comparison facts for 2 to 4 selected candidates.
    """
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2 or len(id_list) > 4:
        raise HTTPException(status_code=400, detail="Comparison requires between 2 and 4 candidate IDs")

    compared = []
    for cid in id_list:
        cand = candidate_repo.get_candidate(cid)
        if cand:
            compared.append(cand)
        else:
            # Check if json exists in processed folder
            import json
            j_path = orchestrator.processed_dir / cid / "resume.json"
            if j_path.exists():
                with open(j_path, "r", encoding="utf-8") as f:
                    compared.append(json.load(f))

    if not compared:
        raise HTTPException(status_code=404, detail="None of the specified candidates were found")

    return {
        "candidate_count": len(compared),
        "candidates": compared
    }

@router.get("/{candidate_id}")
def get_candidate_detail(candidate_id: str):
    """
    Retrieves full candidate detail including education, experience breakdown,
    publications, rule evaluations, and traceable source evidence.
    """
    cand = candidate_repo.get_candidate(candidate_id)
    if not cand:
        # Check disk cache
        import json
        j_path = orchestrator.processed_dir / candidate_id / "resume.json"
        if j_path.exists():
            with open(j_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    return cand

@router.delete("/clear-all")
def clear_all_candidates_endpoint():
    """
    Clears all candidates, screening records, review items, and processed cache from the platform.
    Does NOT delete original input resumes.
    """
    count = candidate_repo.clear_all_candidates()
    return {
        "status": "success",
        "message": f"Successfully cleared all data for {count} candidates",
        "deleted_count": count
    }

@router.delete("/{candidate_id}")
def delete_single_candidate_endpoint(candidate_id: str):
    """
    Removes a single candidate, their screening evaluation, and generated files.
    """
    success = candidate_repo.delete_candidate(candidate_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found or could not be deleted")
    return {
        "status": "success",
        "message": f"Candidate {candidate_id} deleted successfully",
        "candidate_id": candidate_id
    }

@router.post("/{candidate_id}/review")
def submit_candidate_review(candidate_id: str, review: ReviewSubmission):
    """
    Submits a recruiter's human verification verdict and notes for a candidate.
    """
    success = candidate_repo.update_review(candidate_id, verdict=review.verdict, notes=review.notes)
    if not success:
        raise HTTPException(status_code=400, detail="Could not update candidate review status")

    return {
        "message": f"Candidate {candidate_id} marked as {review.verdict}",
        "candidate_id": candidate_id,
        "verdict": review.verdict
    }
