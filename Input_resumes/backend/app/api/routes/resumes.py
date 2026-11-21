import os
import shutil
import time
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse

from backend.app.core.config import settings
from backend.app.pipelines.orchestrator import orchestrator
from backend.app.agents.orchestration_agent import orchestration_agent
from backend.app.repositories.candidate_repo import candidate_repo
from backend.app.models.db_models import init_db

router = APIRouter(prefix="/resumes", tags=["Resumes"])

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

@router.get("/{candidate_id}")
def get_resume_meta(candidate_id: str):
    cand_dir = orchestrator.processed_dir / candidate_id
    ref_path = cand_dir / "original_reference.json"

    if not ref_path.exists():
        raise HTTPException(status_code=404, detail="Resume record not found")

    import json
    with open(ref_path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/{candidate_id}/result")
def get_resume_result(candidate_id: str):
    cand_dir = orchestrator.processed_dir / candidate_id
    json_path = cand_dir / "resume.json"
    md_path = cand_dir / "resume.md"

    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Processed resume result not found")

    import json
    with open(json_path, "r", encoding="utf-8") as f:
        profile_data = json.load(f)

    markdown_text = ""
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_text = f.read()

    return {
        "candidate_id": candidate_id,
        "profile": profile_data,
        "markdown": markdown_text
    }

@router.get("/{candidate_id}/file")
def get_resume_raw_file(candidate_id: str):
    cand_dir = orchestrator.processed_dir / candidate_id
    ref_path = cand_dir / "original_reference.json"

    if not ref_path.exists():
        discovered = orchestrator.discover_resumes()
        for p in discovered:
            if orchestrator.generate_candidate_id(p) == candidate_id:
                return FileResponse(p, filename=p.name)
        raise HTTPException(status_code=404, detail="Source file not found")

    import json
    with open(ref_path, "r", encoding="utf-8") as f:
        ref_data = json.load(f)

    original_path = Path(ref_data.get("original_path", ""))
    if not original_path.exists():
        raise HTTPException(status_code=404, detail="File on disk not accessible")

    return FileResponse(original_path, filename=original_path.name)

@router.post("/{candidate_id}/process")
def process_single_resume(candidate_id: str, force: bool = False):
    discovered = orchestrator.discover_resumes()
    target_file = None
    for p in discovered:
        if orchestrator.generate_candidate_id(p) == candidate_id:
            target_file = p
            break

    if not target_file:
        raise HTTPException(status_code=404, detail=f"No matching file found for candidate ID {candidate_id}")

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
    def _run_batch():
        init_db()
        profiles = orchestrator.process_all_resumes(force_reprocess=force, max_count=max_count)
        for prof in profiles:
            try:
                candidate_repo.save_profile(prof)
            except Exception as e:
                print(f"Error saving {prof.candidate_id}: {e}")

    background_tasks.add_task(_run_batch)

    discovered = orchestrator.discover_resumes()
    count_to_process = min(len(discovered), max_count) if max_count else len(discovered)

    return {
        "status": "queued",
        "message": f"Started processing {count_to_process} resumes in background",
        "total_resumes_discovered": len(discovered)
    }

@router.post("/upload")
def upload_resume(file: UploadFile = File(...)):
    """
    Uploads a single resume into data/uploads/ and screens it immediately using the agentic pipeline.
    """
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Allowed: {', '.join(allowed_exts)}")

    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / file.filename
    counter = 1
    while dest_path.exists():
        stem = Path(file.filename).stem
        dest_path = upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

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
    Uploads multiple PDFs at once, processes them through the distributed Groq key pool
    with rate-limit pacing, marks them as uploaded, and returns the curated results.
    """
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg"}
    upload_dir = settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    processed_candidates = []
    errors = []

    for file in files:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in allowed_exts:
            errors.append({"file": file.filename, "error": "Unsupported file format"})
            continue

        dest_path = upload_dir / file.filename
        counter = 1
        while dest_path.exists():
            stem = Path(file.filename).stem
            dest_path = upload_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # Process through agentic pipeline with Groq Key Pool
            profile = orchestration_agent.process_document(dest_path, force_reprocess=True)
            candidate_repo.save_profile(profile, is_uploaded=True)

            processed_candidates.append({
                "candidate_id": profile.candidate_id,
                "name": profile.name,
                "filename": dest_path.name,
                "highest_degree": profile.education[0].normalized_degree if profile.education else "Unspecified",
                "institution": profile.education[0].institution_normalized or profile.education[0].institution if profile.education else "-",
                "category": profile.education[0].institution_category if profile.education else "Other",
                "teaching_years": profile.experience.teaching_years,
                "research_years": profile.experience.research_years,
                "publications_count": len(profile.research.publications),
                "eligibility_status": profile.screening.eligibility_status,
                "overall_score": profile.screening.overall_score,
                "confidence": profile.screening.confidence
            })

            # Small inter-document pace (0.3s) to keep Groq token velocity completely safe
            time.sleep(0.3)

        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})

    return {
        "total_uploaded": len(files),
        "successfully_processed": len(processed_candidates),
        "candidates": processed_candidates,
        "errors": errors
    }
