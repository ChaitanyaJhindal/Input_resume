import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.config import settings, config_manager
from backend.app.database.repository import candidate_repo
from backend.app.services.institution_service import institution_service
from backend.app.services.screening_service import screening_service
from backend.app.utils.json_utils import atomic_write_text

router = APIRouter(prefix="/settings", tags=["Settings"])

_ALLOWED_RULE_OPERATORS = {"==", "!=", ">=", "<=", ">", "<", "in", "not_in", "contains", "regex"}

class RuleUpdatePayload(BaseModel):
    rules: List[Dict[str, Any]]
    settings: Dict[str, Any]
    version: Optional[str] = None
    department: Optional[str] = None
    academic_year: Optional[str] = None

class PromptsUpdatePayload(BaseModel):
    prompts: Dict[str, Any]

@router.get("/rules")
def get_screening_rules():
    """
    Returns current screening rules configuration.
    """
    return screening_service.rules_config

@router.patch("/rules")
def update_screening_rules(payload: RuleUpdatePayload):
    """
    Validates and atomically updates screening_rules.yaml and reloads the engine.
    """
    for rule in payload.rules:
        if not isinstance(rule, dict) or not rule.get("id") or not rule.get("field"):
            raise HTTPException(status_code=400, detail="Each rule must specify 'id' and 'field'")
        op = rule.get("operator", "==")
        if op not in _ALLOWED_RULE_OPERATORS:
            raise HTTPException(status_code=400, detail=f"Unsupported rule operator: '{op}'")

    config_path = settings.config_dir / "screening_rules.yaml"
    try:
        existing = screening_service.rules_config or {}
        new_data = {
            "version": payload.version or existing.get("version", "1.0.0"),
            "department": payload.department or existing.get("department", "Faculty Pool"),
            "academic_year": payload.academic_year or existing.get("academic_year", "2025-2026"),
            "rules": payload.rules,
            "settings": payload.settings
        }
        serialized = yaml.dump(new_data, sort_keys=False, allow_unicode=True)
        atomic_write_text(config_path, serialized)

        screening_service.reload_rules()
        return {"status": "success", "message": "Screening rules updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rules: {e}")

@router.get("/llm")
def get_llm_config():
    """
    Returns the modular LLM configuration (models, pool, JEV, and per-task overrides).
    """
    return {
        "config": config_manager.llm_config,
        "resolved_models": config_manager.get_resolved_task_models(),
        "groq_models": config_manager.get_groq_models(),
    }

@router.patch("/llm")
def update_llm_config(payload: Dict[str, Any]):
    """
    Updates config/llm_config.yaml and hot-reloads active agents and extractors.
    """
    try:
        updated = config_manager.update_llm_config(payload)
        return {
            "status": "success",
            "message": "LLM configuration updated and reloaded",
            "config": updated,
            "resolved_models": config_manager.get_resolved_task_models(),
            "groq_models": config_manager.get_groq_models(),
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update LLM config: {e}")

@router.get("/prompts")
def get_prompts_config():
    """
    Returns all configurable prompt templates from config/prompts.yaml.
    """
    return {"prompts": config_manager.prompts}

@router.patch("/prompts")
def update_prompts_config(payload: Dict[str, Any]):
    """
    Updates config/prompts.yaml and hot-reloads prompt templates.
    """
    try:
        prompts_data = payload.get("prompts", payload)
        updated = config_manager.update_prompts(prompts_data)
        return {
            "status": "success",
            "message": "Prompts updated and reloaded",
            "prompts": updated,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompts: {e}")

@router.get("/app")
def get_app_config():
    """
    Returns application taxonomies, pipeline limits, and review thresholds.
    """
    return config_manager.app_config

@router.patch("/app")
def update_app_config(payload: Dict[str, Any]):
    """
    Updates config/app_config.yaml and reloads application settings.
    """
    try:
        updated = config_manager.update_app_config(payload)
        return {
            "status": "success",
            "message": "App configuration updated and reloaded",
            "config": updated,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update app config: {e}")

@router.post("/reload")
def reload_all_configs():
    """
    Reloads all YAML configuration files from disk without restarting the server.
    """
    config_manager.reload()
    screening_service.reload_rules()
    return {
        "status": "success",
        "message": "All configuration files reloaded from disk",
        "resolved_models": config_manager.get_resolved_task_models(),
    }

@router.get("/institutions")
def list_institutions():
    """
    Returns the loaded institutions taxonomy database.
    """
    return {
        "categories": institution_service.categories,
        "institutions": institution_service.institutions_db
    }

@router.get("/system-status")
def get_system_status():
    """
    Returns system status, active models, and mock mode indicators.
    """
    groq_keys = settings.get_all_groq_keys()
    return {
        "environment": settings.environment,
        "mock_mode": settings.mock_mode,
        "groq_vision_model": config_manager.resolve_model("vision"),
        "groq_reasoning_model": config_manager.resolve_model("reasoning"),
        "groq_advanced_model": config_manager.resolve_model("advanced"),
        "groq_configured": len(groq_keys) > 0,
        "groq_keys_count": len(groq_keys),
        "typesafe_jev_model": config_manager.get_jev_config()["model"],
        "typesafe_configured": bool(settings.typesafe_api_key and len(settings.typesafe_api_key) > 5),
        "resumes_directory": str(Path(settings.resumes_dir).resolve()),
        "database": settings.database_url,
        "resolved_task_models": config_manager.get_resolved_task_models(),
    }


@router.delete("/reset-workspace")
def reset_workspace(
    include_jds: bool = Query(True),
    include_source_resumes: bool = Query(False),
):
    """
    Clears candidates, screening records, audit logs, processed/uploaded artifacts,
    and optionally Job Descriptions and Input_resumes files so the user can start from scratch.
    Always preserves data/institutions/institutions.json and config/*.yaml files.
    """
    try:
        stats = candidate_repo.reset_workspace(
            include_jds=include_jds,
            include_source_resumes=include_source_resumes,
        )
        return {
            "status": "success",
            "candidates_deleted": stats["candidates_deleted"],
            "jds_deleted": stats["jds_deleted"],
            "source_files_deleted": stats["source_files_deleted"],
            "message": (
                f"Cleared {stats['candidates_deleted']} candidates, "
                f"{stats['jds_deleted']} job descriptions, and "
                f"{stats['source_files_deleted']} source resume files."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset workspace: {e}")
