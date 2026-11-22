import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks

from backend.app.agents.evaluation_agent import evaluation_agent
from backend.app.agents.jd_agent import jd_agent
from backend.app.database.jd_repository import jd_repo
from fastapi.responses import FileResponse

from backend.app.config import settings, config_manager
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.agents.orchestration_agent import orchestration_agent
from backend.app.database.repository import candidate_repo
from backend.app.database.models import init_db
from backend.app.services.education_service import EducationService
from backend.app.utils.json_utils import safe_child_path, sanitize_filename, validate_candidate_id

logger = logging.getLogger("FacultyScreen.ResumesRoute")

router = APIRouter(prefix="/resumes", tags=["Resumes"])

_sync_lock = threading.Lock()
_sync_state: Dict[str, Any] = {
    "running": False,
    "total": 0,
    "completed": 0,
    "failed": 0,
    "current_file": None,
    "started_at": None,
    "finished_at": None,
    "last_error": None,
}


def _validate_cand_id_or_400(candidate_id: str) -> str:
    try:
        return validate_candidate_id(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid candidate ID format: {candidate_id}")


def _resolve_stored_file_path(raw_path: str, candidate_id: str) -> Optional[Path]:
    """Resolve stored file path across relative base_dir, uploads/, resumes_dir, or candidate_id."""
    if raw_path:
        p = Path(raw_path)
        if p.is_absolute() and p.exists():
            return p
        rel_candidate = settings.base_dir / raw_path
        if rel_candidate.exists():
            return rel_candidate
        upload_candidate = settings.data_dir / "uploads" / p.name
        if upload_candidate.exists():
            return upload_candidate
        source_candidate = orchestrator.resumes_dir / p.name
        if source_candidate.exists():
            return source_candidate

    cand = candidate_repo.get_candidate(candidate_id)
    if cand:
        for alt in (cand.get("file_path"), cand.get("file_name")):
            if alt:
                ap = Path(alt)
                if ap.is_absolute() and ap.exists():
                    return ap
                for root in (settings.base_dir, settings.data_dir / "uploads", orchestrator.resumes_dir):
                    cand_p = root / ap.name if root != settings.base_dir else root / alt
                    if cand_p.exists():
                        return cand_p

    for p in orchestrator.discover_resumes():
        if orchestrator.generate_candidate_id(p) == candidate_id:
            return p
        if cand and cand.get("file_name") and p.name == cand.get("file_name"):
            return p
    return None


def _save_or_reuse_upload(file: UploadFile, upload_dir: Path, max_size_bytes: int = 25 * 1024 * 1024) -> Path:
    """Validate upload size/filename and save or reuse identical-content file inside upload_dir."""
    content = file.file.read(max_size_bytes + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > max_size_bytes:
        max_mb = round(max_size_bytes / (1024 * 1024))
        raise HTTPException(status_code=413, detail=f"Uploaded file exceeds maximum allowed size of {max_mb} MB")

    content_hash = hashlib.sha256(content).hexdigest()

    for existing in upload_dir.iterdir():
        if existing.is_file() and existing.stat().st_size == len(content):
            if orchestration_agent.compute_file_hash(existing) == content_hash:
                return existing

    safe_name = sanitize_filename(file.filename)
    suffix = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem
    dest_path = safe_child_path(upload_dir, safe_name)
    counter = 1
    while dest_path.exists():
        dest_path = safe_child_path(upload_dir, f"{stem}_{counter}{suffix}")
        counter += 1

    with open(dest_path, "wb") as buffer:
        buffer.write(content)
    return dest_path

@router.get("")
def list_resumes():
    """
    Lists all detected resumes in the source-of-truth directory along with processing status.
    """
    discovered = orchestrator.discover_resumes()
    resumes_list = []

    for file_path in discovered:
        cand_id = orchestrator.generate_candidate_id(file_path)
        is_processed = (orchestrator.processed_dir / cand_id / "resume.json").exists()

        resumes_list.append({
            "candidate_id": cand_id,
            "filename": file_path.name,
            "file_size": file_path.stat().st_size,
            "extension": file_path.suffix.lower(),
            "status": "processed" if is_processed else "unprocessed",
            "path": str(file_path.resolve())
        })

    return {
        "source_directory": str(orchestrator.resumes_dir),
        "total_count": len(resumes_list),
        "processed_count": sum(1 for r in resumes_list if r["status"] == "processed"),
        "resumes": resumes_list
    }

@router.get("/sync-status")
def get_sync_status():
    """
    Returns live background sync progress for Input_resumes processing.
    """
    with _sync_lock:
        return dict(_sync_state)


@router.get("/{candidate_id}")
def get_resume_meta(candidate_id: str):
    cid = _validate_cand_id_or_400(candidate_id)
    cand_dir = safe_child_path(orchestrator.processed_dir, cid)
    ref_path = cand_dir / "original_reference.json"

    if not ref_path.exists():
        raise HTTPException(status_code=404, detail="Resume record not found")

    with open(ref_path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/{candidate_id}/result")
def get_resume_result(candidate_id: str):
    cid = _validate_cand_id_or_400(candidate_id)
    cand_dir = safe_child_path(orchestrator.processed_dir, cid)
    json_path = cand_dir / "resume.json"
    md_path = cand_dir / "resume.md"

    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Processed resume result not found")

    with open(json_path, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    markdown_text = ""
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_text = f.read()

    return {
        "candidate_id": cid,
        "profile": profile_data,
        "markdown": markdown_text
    }

@router.get("/{candidate_id}/file")
def get_resume_raw_file(candidate_id: str):
    cid = _validate_cand_id_or_400(candidate_id)
    cand_dir = safe_child_path(orchestrator.processed_dir, cid)
    ref_path = cand_dir / "original_reference.json"

    raw_path = ""
    if ref_path.exists():
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_data = json.load(f)
        raw_path = ref_data.get("original_path", "") or ref_data.get("original_filename", "")

    resolved = _resolve_stored_file_path(raw_path, cid)
    if not resolved or not resolved.exists():
        raise HTTPException(status_code=404, detail="File on disk not accessible")

    return FileResponse(resolved, filename=resolved.name)

@router.post("/{candidate_id}/process")
def process_single_resume(candidate_id: str, force: bool = False):
    cid = _validate_cand_id_or_400(candidate_id)
    discovered = orchestrator.discover_resumes()
    target_file = None
    for p in discovered:
        if orchestrator.generate_candidate_id(p) == cid:
            target_file = p
            break

    if not target_file:
        raise HTTPException(status_code=404, detail=f"No matching file found for candidate ID {cid}")

    profile = orchestration_agent.process_document(target_file, force_reprocess=force)
    candidate_repo.save_profile(profile)

    return {
        "message": f"Successfully processed {target_file.name}",
        "candidate_id": profile.candidate_id,
        "eligibility_status": profile.screening.eligibility_status,
        "overall_score": profile.screening.overall_score
    }

@router.post("/process-all")
def process_all_resumes_endpoint(background_tasks: BackgroundTasks, force: bool = False, max_count: Optional[int] = None):
    discovered = orchestrator.discover_resumes()
    files_to_process = discovered[:max_count] if max_count else discovered

    with _sync_lock:
        if _sync_state["running"]:
            return {
                "status": "already_running",
                "message": "A background resume sync is already in progress",
                "total_resumes_discovered": len(discovered),
                "sync": dict(_sync_state),
            }
        _sync_state.update({
            "running": True,
            "total": len(files_to_process),
            "completed": 0,
            "failed": 0,
            "current_file": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "last_error": None,
        })

    def _run_batch():
        init_db()
        try:
            for file_path in files_to_process:
                with _sync_lock:
                    _sync_state["current_file"] = file_path.name
                try:
                    prof = orchestration_agent.process_document(file_path, force_reprocess=force)
                    candidate_repo.save_profile(prof)
                    with _sync_lock:
                        _sync_state["completed"] += 1
                except Exception as e:
                    with _sync_lock:
                        _sync_state["failed"] += 1
                        _sync_state["last_error"] = f"{file_path.name}: {e}"
                    logger.error(f"Error processing/saving {file_path.name}: {e}", exc_info=True)
        finally:
            with _sync_lock:
                _sync_state["running"] = False
                _sync_state["current_file"] = None
                _sync_state["finished_at"] = datetime.now(timezone.utc).isoformat()

    background_tasks.add_task(_run_batch)

    return {
        "status": "queued",
        "message": f"Started processing {len(files_to_process)} resumes in background",
        "total_resumes_discovered": len(discovered)
    }

@router.post("/upload")
def upload_resume(file: UploadFile = File(...)):
    """
    Uploads a single resume into data/uploads/ and screens it immediately using the agentic pipeline.
    """
    pipeline_cfg = config_manager.get_pipeline_config()
    allowed_exts = set(pipeline_cfg["supported_extensions"])
    max_size_bytes = int(pipeline_cfg["max_upload_size_mb"]) * 1024 * 1024
    safe_name = sanitize_filename(file.filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Allowed: {', '.join(sorted(allowed_exts))}")

    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = _save_or_reuse_upload(file, upload_dir, max_size_bytes=max_size_bytes)

    profile = orchestration_agent.process_document(dest_path, force_reprocess=True)
    candidate_repo.save_profile(profile, is_uploaded=True)

    return {
        "message": "Resume uploaded and screened successfully",
        "candidate_id": profile.candidate_id,
        "filename": dest_path.name,
        "eligibility_status": profile.screening.eligibility_status,
        "overall_score": profile.screening.overall_score
    }

@router.post("/upload-batch")
def upload_batch_resumes(files: List[UploadFile] = File(...)):
    """
    Uploads multiple resumes at once, validates sizes/formats, processes them through the
    agentic pipeline, marks them as uploaded, and returns curated results + per-file errors.
    """
    pipeline_cfg = config_manager.get_pipeline_config()
    allowed_exts = set(pipeline_cfg["supported_extensions"])
    max_size_bytes = int(pipeline_cfg["max_upload_size_mb"]) * 1024 * 1024
    batch_delay = float(pipeline_cfg["batch_upload_delay_seconds"])
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    processed_candidates = []
    errors = []

    for file in files:
        safe_name = sanitize_filename(file.filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in allowed_exts:
            errors.append({"filename": safe_name, "file": safe_name, "error": "Unsupported file format"})
            continue

        try:
            dest_path = _save_or_reuse_upload(file, upload_dir, max_size_bytes=max_size_bytes)
            profile = orchestration_agent.process_document(dest_path, force_reprocess=True)
            candidate_repo.save_profile(profile, is_uploaded=True)
            top_edu = EducationService.select_highest_education(profile.education)

            processed_candidates.append({
                "candidate_id": profile.candidate_id,
                "name": profile.name,
                "filename": dest_path.name,
                "highest_degree": top_edu.normalized_degree if top_edu else "Unspecified",
                "institution": (top_edu.institution_normalized or top_edu.institution) if top_edu else "-",
                "category": top_edu.institution_category if top_edu else "Other",
                "teaching_years": profile.experience.teaching_years,
                "research_years": profile.experience.research_years,
                "publications_count": len(profile.research.publications),
                "eligibility_status": profile.screening.eligibility_status,
                "overall_score": profile.screening.overall_score,
                "confidence": profile.screening.confidence
            })

            if batch_delay > 0:
                time.sleep(batch_delay)

        except HTTPException as http_err:
            errors.append({"filename": safe_name, "file": safe_name, "error": str(http_err.detail)})
        except Exception as e:
            errors.append({"filename": safe_name, "file": safe_name, "error": str(e)})

    return {
        "total_uploaded": len(files),
        "successfully_processed": len(processed_candidates),
        "candidates": processed_candidates,
        "errors": errors
    }


@router.post("/upload-with-jd")
def upload_resumes_with_jd(
    files: List[UploadFile] = File(...),
    jd_id: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    jd_title: Optional[str] = Form(None),
    jd_department: Optional[str] = Form(None),
):
    """
    Dual-upload endpoint: accepts a Job Description (saved jd_id, file, or text) alongside
    1..N candidate resumes, processes & validates each CV, and evaluates every candidate
    dynamically against the target JD.
    """
    resolved_jd_record: Optional[Dict[str, Any]] = None
    if jd_id:
        clean_jd = _validate_cand_id_or_400(jd_id)
        resolved_jd_record = jd_repo.get_jd(clean_jd)
        if not resolved_jd_record:
            raise HTTPException(status_code=404, detail=f"Job description {clean_jd} not found")
    else:
        raw_jd_text = (jd_text or "").strip()
        saved_jd_name: Optional[str] = None
        saved_jd_path: Optional[str] = None
        if jd_file is not None and jd_file.filename:
            safe_jd_name = sanitize_filename(jd_file.filename, fallback="jd.txt")
            jd_suffix = Path(safe_jd_name).suffix.lower()
            if jd_suffix not in {".pdf", ".docx", ".txt", ".md"}:
                raise HTTPException(status_code=400, detail=f"Unsupported JD format '{jd_suffix}'")
            max_bytes = int(config_manager.get_pipeline_config()["max_upload_size_mb"]) * 1024 * 1024
            jd_bytes = jd_file.file.read(max_bytes + 1)
            if not jd_bytes:
                raise HTTPException(status_code=400, detail="Uploaded JD file is empty")
            if len(jd_bytes) > max_bytes:
                raise HTTPException(status_code=413, detail="Uploaded JD file exceeds size limit")
            jd_dir = settings.data_dir / "jds"
            jd_dir.mkdir(parents=True, exist_ok=True)
            jd_dest = safe_child_path(jd_dir, safe_jd_name)
            with open(jd_dest, "wb") as f:
                f.write(jd_bytes)
            saved_jd_name = jd_dest.name
            saved_jd_path = str(jd_dest)
            raw_jd_text = jd_agent.extract_text_from_file(jd_dest)

        if len(raw_jd_text) < 20:
            raise HTTPException(status_code=400, detail="A Job Description (jd_id, jd_file, or jd_text >= 20 chars) is required")

        spec = jd_agent.parse_jd(raw_jd_text, title_hint=jd_title, department_hint=jd_department)
        resolved_jd_record = jd_repo.save_jd(
            spec, raw_text=raw_jd_text, file_name=saved_jd_name, file_path=saved_jd_path
        )

    jd_spec = jd_repo.get_jd_spec(resolved_jd_record["jd_id"])
    assert jd_spec is not None

    pipeline_cfg = config_manager.get_pipeline_config()
    allowed_exts = set(pipeline_cfg["supported_extensions"])
    max_size_bytes = int(pipeline_cfg["max_upload_size_mb"]) * 1024 * 1024
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    processed_candidates = []
    errors = []

    for file in files:
        safe_name = sanitize_filename(file.filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in allowed_exts:
            errors.append({"filename": safe_name, "file": safe_name, "error": "Unsupported file format"})
            continue

        try:
            dest_path = _save_or_reuse_upload(file, upload_dir, max_size_bytes=max_size_bytes)
            profile = orchestration_agent.process_document(dest_path, force_reprocess=True)
            candidate_repo.save_profile(profile, is_uploaded=True)
            jd_eval = evaluation_agent.evaluate_candidate_against_jd(jd_spec, profile)
            saved_eval = jd_repo.save_evaluation(jd_eval)
            top_edu = EducationService.select_highest_education(profile.education)

            processed_candidates.append({
                "candidate_id": profile.candidate_id,
                "name": profile.name,
                "filename": dest_path.name,
                "highest_degree": top_edu.normalized_degree if top_edu else "Unspecified",
                "institution": (top_edu.institution_normalized or top_edu.institution) if top_edu else "-",
                "category": top_edu.institution_category if top_edu else "Other",
                "eligibility_status": profile.screening.eligibility_status,
                "overall_score": profile.screening.overall_score,
                "dynamic_score": saved_eval["dynamic_score"],
                "recommendation_tier": saved_eval["recommendation_tier"],
                "jd_evaluation": saved_eval,
            })
        except HTTPException as http_err:
            errors.append({"filename": safe_name, "file": safe_name, "error": str(http_err.detail)})
        except Exception as e:
            errors.append({"filename": safe_name, "file": safe_name, "error": str(e)})

    return {
        "jd": resolved_jd_record,
        "total_uploaded": len(files),
        "successfully_processed": len(processed_candidates),
        "candidates": processed_candidates,
        "errors": errors,
    }
