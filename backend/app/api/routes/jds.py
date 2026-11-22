import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.agents.evaluation_agent import evaluation_agent
from backend.app.agents.jd_agent import jd_agent
from backend.app.config import config_manager, settings
from backend.app.database.jd_repository import jd_repo
from backend.app.database.models import init_db
from backend.app.database.repository import candidate_repo
from backend.app.schemas.jd import JDApprovalStatus
from backend.app.utils.json_utils import safe_child_path, sanitize_filename, validate_candidate_id

logger = logging.getLogger("FacultyScreen.JDsRoute")

router = APIRouter(prefix="/jds", tags=["Job Descriptions"])

_eval_lock = threading.Lock()
_eval_state: Dict[str, Dict[str, Any]] = {}

_ALLOWED_JD_EXTS = {".pdf", ".docx", ".txt", ".md"}


class JDUpdatePayload(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    level: Optional[str] = None
    role_archetype: Optional[str] = None
    summary: Optional[str] = None
    requirements: Optional[List[Dict[str, Any]]] = None
    required_domains: Optional[List[str]] = None
    preferred_courses: Optional[List[str]] = None
    research_expectations: Optional[str] = None
    industry_practice_value: Optional[str] = None
    allow_compensating_strengths: Optional[bool] = None
    weights: Optional[Dict[str, float]] = None


class JDEvaluatePayload(BaseModel):
    candidate_ids: Optional[List[str]] = None
    all_candidates: bool = True


class JDApprovalPayload(BaseModel):
    approval_status: JDApprovalStatus
    notes: Optional[str] = None


def _validate_id_or_400(identifier: str, label: str = "ID") -> str:
    try:
        return validate_candidate_id(identifier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label} format: {identifier}")


@router.post("/upload")
def upload_or_create_jd(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
):
    """Upload a JD document (.pdf, .docx, .txt, .md) or paste raw text to build a structured JD rubric."""
    extracted_text = (raw_text or "").strip()
    saved_name: Optional[str] = None
    saved_path: Optional[str] = None

    if file is not None and file.filename:
        safe_name = sanitize_filename(file.filename, fallback="job_description.txt")
        suffix = Path(safe_name).suffix.lower()
        if suffix not in _ALLOWED_JD_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported JD format '{suffix}'. Allowed: {', '.join(sorted(_ALLOWED_JD_EXTS))}",
            )
        max_bytes = int(config_manager.get_pipeline_config()["max_upload_size_mb"]) * 1024 * 1024
        content = file.file.read(max_bytes + 1)
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded JD file is empty")
        if len(content) > max_bytes:
            raise HTTPException(status_code=413, detail="Uploaded JD file exceeds maximum size limit")

        jd_dir = settings.data_dir / "jds"
        jd_dir.mkdir(parents=True, exist_ok=True)
        dest = safe_child_path(jd_dir, safe_name)
        with open(dest, "wb") as f:
            f.write(content)
        saved_name = dest.name
        saved_path = str(dest)
        try:
            extracted_text = jd_agent.extract_text_from_file(dest)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not extract text from JD file: {e}")

    if len(extracted_text) < 20:
        raise HTTPException(status_code=400, detail="Please provide a valid JD file or text (at least 20 characters)")

    spec = jd_agent.parse_jd(extracted_text, title_hint=title, department_hint=department)
    record = jd_repo.save_jd(spec, raw_text=extracted_text, file_name=saved_name, file_path=saved_path)
    return {"status": "success", "jd": record}


@router.get("")
def list_jds():
    return {"jds": jd_repo.list_jds()}


@router.get("/{jd_id}")
def get_jd_detail(jd_id: str):
    clean_jd = _validate_id_or_400(jd_id, "jd_id")
    jd = jd_repo.get_jd(clean_jd)
    if not jd:
        raise HTTPException(status_code=404, detail=f"Job description {clean_jd} not found")
    return jd


@router.patch("/{jd_id}")
def update_jd_spec(jd_id: str, payload: JDUpdatePayload):
    clean_jd = _validate_id_or_400(jd_id, "jd_id")
    patch_dict = payload.model_dump(exclude_none=True)
    updated = jd_repo.update_jd(clean_jd, patch_dict)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Job description {clean_jd} not found")
    return {"status": "success", "jd": updated}


@router.delete("/{jd_id}")
def delete_jd(jd_id: str):
    clean_jd = _validate_id_or_400(jd_id, "jd_id")
    if not jd_repo.delete_jd(clean_jd):
        raise HTTPException(status_code=404, detail=f"Job description {clean_jd} not found")
    return {"status": "success", "jd_id": clean_jd}


@router.get("/{jd_id}/evaluate-status")
def get_evaluate_status(jd_id: str):
    clean_jd = _validate_id_or_400(jd_id, "jd_id")
    with _eval_lock:
        state = _eval_state.get(
            clean_jd,
            {"running": False, "total": 0, "completed": 0, "failed": 0, "current_candidate": None, "last_error": None},
        )
        return dict(state)


@router.post("/{jd_id}/evaluate")
def evaluate_candidates_for_jd(
    jd_id: str,
    background_tasks: BackgroundTasks,
    payload: Optional[JDEvaluatePayload] = None,
):
    clean_jd = _validate_id_or_400(jd_id, "jd_id")
    spec = jd_repo.get_jd_spec(clean_jd)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Job description {clean_jd} not found")

    if payload and payload.candidate_ids:
        target_ids = [_validate_id_or_400(cid, "candidate_id") for cid in payload.candidate_ids]
    else:
        target_ids = candidate_repo.list_all_candidate_ids()

    # Synchronous fast path when evaluating up to 5 specific candidates
    if len(target_ids) <= 5:
        evaluated = []
        for cid in target_ids:
            prof = jd_repo.load_profile_for_candidate(cid)
            if not prof:
                continue
            ev = evaluation_agent.evaluate_candidate_against_jd(spec, prof)
            saved_ev = jd_repo.save_evaluation(ev)
            evaluated.append(saved_ev)
        return {
            "status": "completed",
            "jd_id": clean_jd,
            "evaluated_count": len(evaluated),
            "evaluations": evaluated,
        }

    with _eval_lock:
        if _eval_state.get(clean_jd, {}).get("running"):
            return {"status": "already_running", "jd_id": clean_jd, **_eval_state[clean_jd]}
        _eval_state[clean_jd] = {
            "running": True,
            "total": len(target_ids),
            "completed": 0,
            "failed": 0,
            "current_candidate": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "last_error": None,
        }

    def _run_eval_batch():
        init_db()
        try:
            for cid in target_ids:
                with _eval_lock:
                    _eval_state[clean_jd]["current_candidate"] = cid
                try:
                    prof = jd_repo.load_profile_for_candidate(cid)
                    if not prof:
                        with _eval_lock:
                            _eval_state[clean_jd]["failed"] += 1
                        continue
                    ev = evaluation_agent.evaluate_candidate_against_jd(spec, prof)
                    jd_repo.save_evaluation(ev)
                    with _eval_lock:
                        _eval_state[clean_jd]["completed"] += 1
                except Exception as err:
                    with _eval_lock:
                        _eval_state[clean_jd]["failed"] += 1
                        _eval_state[clean_jd]["last_error"] = f"{cid}: {err}"
                    logger.error(f"JD evaluation error for {cid} vs {clean_jd}: {err}")
        finally:
            with _eval_lock:
                _eval_state[clean_jd]["running"] = False
                _eval_state[clean_jd]["current_candidate"] = None
                _eval_state[clean_jd]["finished_at"] = datetime.now(timezone.utc).isoformat()

    background_tasks.add_task(_run_eval_batch)
    return {
        "status": "queued",
        "jd_id": clean_jd,
        "total": len(target_ids),
        "message": f"Evaluating {len(target_ids)} candidates against '{spec.title}' in background",
    }


@router.get("/{jd_id}/candidates")
def get_candidates_for_jd(jd_id: str):
    clean_jd = _validate_id_or_400(jd_id, "jd_id")
    jd = jd_repo.get_jd(clean_jd)
    if not jd:
        raise HTTPException(status_code=404, detail=f"Job description {clean_jd} not found")

    items = jd_repo.list_evaluations_for_jd(clean_jd)
    summary = {
        "total_evaluated": len(items),
        "strong_match": sum(1 for c in items if (c.get("jd_evaluation") or {}).get("recommendation_tier") == "strong_match"),
        "strong_alternative_fit": sum(1 for c in items if (c.get("jd_evaluation") or {}).get("recommendation_tier") == "strong_alternative_fit"),
        "conditional_review": sum(1 for c in items if (c.get("jd_evaluation") or {}).get("recommendation_tier") == "conditional_review"),
        "low_alignment": sum(1 for c in items if (c.get("jd_evaluation") or {}).get("recommendation_tier") == "low_alignment"),
        "approved_count": sum(1 for c in items if (c.get("jd_evaluation") or {}).get("approval_status") in {"approved", "approved_alternative", "interview_recommended"}),
    }
    return {"jd": jd, "summary": summary, "candidates": items}


@router.post("/{jd_id}/candidates/{candidate_id}/approval")
def submit_jd_candidate_approval(
    jd_id: str,
    candidate_id: str,
    payload: JDApprovalPayload,
):
    clean_jd = _validate_id_or_400(jd_id, "jd_id")
    clean_cand = _validate_id_or_400(candidate_id, "candidate_id")
    updated = jd_repo.update_approval(
        clean_jd,
        clean_cand,
        approval_status=payload.approval_status,
        notes=payload.notes,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Evaluation record not found for candidate and JD")
    return {"status": "success", "evaluation": updated}
