from typing import List, Literal, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.database.jd_repository import jd_repo
from backend.app.database.repository import candidate_repo
from backend.app.groq.extractor import groq_extractor
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.services.academic_profile_service import academic_profile_service
from backend.app.utils.json_utils import safe_child_path, validate_candidate_id
from backend.app.utils.link_extractor import extract_academic_links

router = APIRouter(prefix="/candidates", tags=["Candidates"])

class ReviewSubmission(BaseModel):
    verdict: Literal["approved", "eligible", "rejected", "disqualified"]
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
    for raw_cid in id_list:
        try:
            cid = validate_candidate_id(raw_cid)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid candidate ID format: {raw_cid}")
        cand = candidate_repo.get_candidate(cid)
        if cand:
            compared.append(cand)
        else:
            import json
            j_path = safe_child_path(orchestrator.processed_dir, cid) / "resume.json"
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
def get_candidate_detail(candidate_id: str, jd_id: Optional[str] = None):
    """
    Retrieves full candidate detail including education, experience breakdown,
    publications, courses taught, academic links, and optional dynamic JD evaluation.
    """
    try:
        cid = validate_candidate_id(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid candidate ID format: {candidate_id}")

    cand = candidate_repo.get_candidate(cid)
    if not cand:
        import json
        j_path = safe_child_path(orchestrator.processed_dir, cid) / "resume.json"
        if j_path.exists():
            with open(j_path, "r", encoding="utf-8") as f:
                cand = json.load(f)
        else:
            raise HTTPException(status_code=404, detail=f"Candidate {cid} not found")

    if jd_id:
        try:
            clean_jd = validate_candidate_id(jd_id)
            ev = jd_repo.get_evaluation(clean_jd, cid)
            if ev:
                cand["jd_evaluation"] = ev
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid jd_id format: {jd_id}")

    return cand


@router.post("/{candidate_id}/enrich-links")
def enrich_candidate_links(candidate_id: str):
    """
    Re-extracts academic profile links from the candidate's raw CV file (including PDF annotations)
    and verifies ORCID / OpenAlex public academic metrics on demand.
    """
    try:
        cid = validate_candidate_id(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid candidate ID format: {candidate_id}")

    prof = jd_repo.load_profile_for_candidate(cid)
    if not prof:
        raise HTTPException(status_code=404, detail=f"Candidate {cid} not found")

    from backend.app.api.routes.resumes import _resolve_stored_file_path

    raw_file = _resolve_stored_file_path(prof.metadata.file_path if prof.metadata else "", cid)
    raw_text = ""
    if raw_file and raw_file.exists():
        raw_text, _ = groq_extractor.extract_raw_text(raw_file)
    fresh_links = extract_academic_links(raw_file, raw_text)
    if fresh_links:
        prof.academic_links = fresh_links

    verification = academic_profile_service.enrich_profile(prof)
    prof.external_verification = verification

    links_dicts = [l.model_dump() for l in prof.academic_links]
    ver_dict = verification.model_dump()
    candidate_repo.update_external_verification(cid, links_dicts, ver_dict)
    updated = candidate_repo.get_candidate(cid)
    return {
        "status": "success",
        "academic_links": links_dicts,
        "external_verification": ver_dict,
        "candidate": updated,
    }

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
    try:
        cid = validate_candidate_id(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid candidate ID format: {candidate_id}")

    success = candidate_repo.delete_candidate(cid)
    if not success:
        raise HTTPException(status_code=404, detail=f"Candidate {cid} not found or could not be deleted")
    return {
        "status": "success",
        "message": f"Candidate {cid} deleted successfully",
        "candidate_id": cid
    }

@router.post("/{candidate_id}/review")
def submit_candidate_review(candidate_id: str, review: ReviewSubmission):
    """
    Submits a recruiter's human verification verdict and notes for a candidate.
    """
    try:
        cid = validate_candidate_id(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid candidate ID format: {candidate_id}")

    success = candidate_repo.update_review(cid, verdict=review.verdict, notes=review.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found or could not be updated")

    return {
        "message": f"Candidate {cid} marked as {review.verdict}",
        "candidate_id": cid,
        "verdict": review.verdict
    }
