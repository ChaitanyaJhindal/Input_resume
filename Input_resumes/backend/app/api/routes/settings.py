import yaml
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.services.institution_service import institution_service
from backend.app.services.screening_service import screening_service

router = APIRouter(prefix="/settings", tags=["Settings"])

class RuleUpdatePayload(BaseModel):
    rules: List[Dict[str, Any]]
    settings: Dict[str, Any]

@router.get("/rules")
def get_screening_rules():
    """
    Returns current screening rules configuration.
    """
    return screening_service.rules_config

@router.patch("/rules")
def update_screening_rules(payload: RuleUpdatePayload):
    """
    Updates screening_rules.yaml and reloads the engine.
    """
    config_path = settings.config_dir / "screening_rules.yaml"
    try:
        new_data = {
            "version": "1.0.0",
            "department": "Faculty Pool",
            "rules": payload.rules,
            "settings": payload.settings
        }
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(new_data, f, sort_keys=False)

        screening_service.reload_rules()
        return {"status": "success", "message": "Screening rules updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rules: {e}")

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
    return {
        "environment": settings.environment,
        "mock_mode": settings.mock_mode,
        "groq_vision_model": settings.groq_vision_model,
        "groq_configured": bool(settings.groq_api_key and settings.groq_api_key.startswith("gsk_")),
        "typesafe_jev_model": settings.jev_model,
        "typesafe_configured": bool(settings.typesafe_api_key and len(settings.typesafe_api_key) > 5),
        "resumes_directory": str(Path(settings.resumes_dir).resolve()),
        "database": settings.database_url
    }
