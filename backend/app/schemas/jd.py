from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.resume import NotableHighlight


RequirementPriority = Literal["must_have", "strong_preference", "nice_to_have"]
RequirementStrictness = Literal["strict", "flexible_with_equivalence"]
RequirementStatus = Literal["met", "partially_met", "compensated", "gap"]
RecommendationTier = Literal[
    "strong_match",
    "strong_alternative_fit",
    "conditional_review",
    "low_alignment",
]
JDApprovalStatus = Literal[
    "pending",
    "approved",
    "approved_alternative",
    "interview_recommended",
    "hold",
    "rejected",
]


class JDRequirement(BaseModel):
    id: str
    category: str = "other"  # qualification, experience, teaching, research, domain_skill, leadership, other
    label: str
    priority: RequirementPriority = "must_have"
    weight: int = 15
    strictness: RequirementStrictness = "flexible_with_equivalence"
    jd_quote: Optional[str] = None


class JDWeights(BaseModel):
    requirement_fit: float = 0.35
    domain_semantic_fit: float = 0.25
    teaching_fit: float = 0.15
    research_and_impact: float = 0.15
    alternative_strength_credit: float = 0.10


class JobDescriptionSpec(BaseModel):
    jd_id: str
    title: str
    department: Optional[str] = None
    level: Optional[str] = None
    role_archetype: str = "balanced"
    summary: Optional[str] = None
    requirements: List[JDRequirement] = Field(default_factory=list)
    required_domains: List[str] = Field(default_factory=list)
    preferred_courses: List[str] = Field(default_factory=list)
    research_expectations: Optional[str] = None
    industry_practice_value: Optional[str] = None
    allow_compensating_strengths: bool = True
    weights: JDWeights = Field(default_factory=JDWeights)


class RequirementMatch(BaseModel):
    requirement_id: str
    label: str
    category: str = "other"
    priority: str = "must_have"
    status: RequirementStatus = "gap"
    score: float = 0.0
    evidence: Optional[str] = None
    rationale: str = ""


class CompensatingStrength(BaseModel):
    missed_requirement: str
    compensating_evidence: str
    rationale: str
    strength_level: str = "strong"  # strong, moderate


class DimensionScores(BaseModel):
    requirement_fit: float = 0.0
    domain_semantic_fit: float = 0.0
    teaching_fit: float = 0.0
    research_and_impact: float = 0.0
    alternative_strength_credit: float = 0.0


class CandidateJDEvaluation(BaseModel):
    jd_id: str
    candidate_id: str
    dynamic_score: float = 0.0
    recommendation_tier: RecommendationTier = "conditional_review"
    confidence: float = 0.85
    grounding_score: float = 1.0
    dimension_scores: DimensionScores = Field(default_factory=DimensionScores)
    requirement_matrix: List[RequirementMatch] = Field(default_factory=list)
    compensating_strengths: List[CompensatingStrength] = Field(default_factory=list)
    standout_highlights: List[NotableHighlight] = Field(default_factory=list)
    executive_brief: str = ""
    interview_probes: List[str] = Field(default_factory=list)
    approval_status: JDApprovalStatus = "pending"
    approval_notes: Optional[str] = None
    approved_by: Optional[str] = None
    evaluated_at: Optional[str] = None
