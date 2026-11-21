from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class JevDecisionRequest(BaseModel):
    task: str  # e.g., "classify_institution", "classify_degree", "evaluate_rule", "check_ambiguity"
    context: Dict[str, Any]
    candidate_options: Optional[List[str]] = None
    confidence_threshold: float = 0.85

class JevDecisionResponse(BaseModel):
    decision: str
    confidence: float = 0.95
    rationale: str
    is_escalated: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = "jev"  # "deterministic", "jev", "llm_escalation", "fallback"

class InstitutionClassificationInput(BaseModel):
    institution_name: str
    country: Optional[str] = "India"
    available_categories: List[str]

class DegreeClassificationInput(BaseModel):
    raw_degree: str
    field_of_study: Optional[str] = None
    available_levels: List[str]

class FastScreeningCheckInput(BaseModel):
    rule_id: str
    field_name: str
    candidate_value: Any
    condition: str
    expected_value: Any
