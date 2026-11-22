from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SourceEvidence(BaseModel):
    field: str
    value: Any
    evidence: str
    source_page: Optional[int] = 1
    confidence: float = 0.95
    position_available: bool = False
    bounding_box: Optional[List[float]] = None

class EducationEntry(BaseModel):
    degree: str
    normalized_degree: str = "Other"  # PhD / Doctorate, Postgraduate / Masters, Undergraduate, etc.
    field: Optional[str] = None
    institution: str
    institution_normalized: Optional[str] = None
    institution_category: Optional[str] = "Other"  # IIT, NIT, Central University, etc.
    institution_tier: Optional[str] = "Unknown / Unclassified"
    start_year: Optional[int] = None
    graduation_year: Optional[int] = None
    thesis_title: Optional[str] = None
    advisor: Optional[str] = None
    gpa_or_honors: Optional[str] = None
    status: str = "completed"
    confidence: float = 0.9
    evidence: Optional[str] = None
    source_page: Optional[int] = 1


class CourseTaughtEntry(BaseModel):
    course_name: str
    course_code: Optional[str] = None
    level: str = "Unspecified"  # UG, PG, PhD, Executive, Unspecified
    institution: Optional[str] = None
    term_or_years: Optional[str] = None
    role: str = "Instructor"
    evidence: Optional[str] = None
    source_page: Optional[int] = 1


class AcademicLink(BaseModel):
    platform: str  # google_scholar, orcid, scopus, linkedin, github, researchgate, dblp, ssrn, website, other
    url: str
    identifier: Optional[str] = None
    source: str = "cv_text"  # pdf_annotation, cv_text, llm_extracted
    verified: bool = False


class SupervisionSummary(BaseModel):
    phd_completed: int = 0
    phd_ongoing: int = 0
    masters_guided: int = 0
    ug_projects_guided: int = 0
    details: List[str] = Field(default_factory=list)


class NotableHighlight(BaseModel):
    category: str = "achievement"
    title: str
    impact: Optional[str] = None
    evidence: Optional[str] = None


class ExternalVerification(BaseModel):
    orcid_verified: bool = False
    openalex_id: Optional[str] = None
    citation_count: Optional[int] = None
    h_index: Optional[int] = None
    i10_index: Optional[int] = None
    works_count: Optional[int] = None
    match_method: str = "none"  # orcid_exact, doi_verified, link_only, none
    verified_at: Optional[str] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None

class ExperienceBreakdown(BaseModel):
    total_years: float = 0.0
    teaching_years: float = 0.0
    research_years: float = 0.0
    industry_years: float = 0.0
    administrative_years: float = 0.0

class EmploymentEntry(BaseModel):
    title: str
    organization: str
    category: str = "teaching"  # teaching, research, industry, administrative
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_years: float = 0.0
    is_current: bool = False
    description: Optional[str] = None
    evidence: Optional[str] = None
    source_page: Optional[int] = 1

class PublicationEntry(BaseModel):
    title: str
    venue: Optional[str] = None  # Journal or Conference name
    year: Optional[int] = None
    doi: Optional[str] = None
    citation_count: Optional[int] = None
    indexed: Optional[str] = None  # Scopus, SCI, Peer-Reviewed
    evidence: Optional[str] = None

class ResearchProfile(BaseModel):
    publications: List[PublicationEntry] = Field(default_factory=list)
    patents: List[Dict[str, Any]] = Field(default_factory=list)
    research_projects: List[Dict[str, Any]] = Field(default_factory=list)
    research_domains: List[str] = Field(default_factory=list)
    books: List[Dict[str, Any]] = Field(default_factory=list)

class RuleEvaluation(BaseModel):
    rule_id: str
    name: str
    status: str  # pass, fail, unknown
    reason: str
    evidence: Optional[str] = None
    confidence: float = 0.95
    is_mandatory: bool = True
    weight: int = 20

class ScreeningResult(BaseModel):
    eligibility_status: str = "needs_review"  # eligible, needs_review, disqualified
    overall_score: float = 0.0
    confidence: float = 0.9
    flags: List[str] = Field(default_factory=list)
    rules_evaluated: List[RuleEvaluation] = Field(default_factory=list)
    decision_path: List[str] = Field(default_factory=list)

class ProcessingMetadata(BaseModel):
    pipeline_version: str = "1.0.0"
    model_name: str = "qwen/qwen3.8-27b"
    file_name: str
    file_path: str
    file_hash: str
    page_count: int = 1
    processing_time_seconds: float = 0.0
    groq_api_calls: int = 0
    jev_decision_calls: int = 0
    deterministic_resolutions: int = 0
    escalations: int = 0
    grounding_score: float = 1.0
    extraction_method: str = "groq_text"
    json_repaired: bool = False
    processed_at: str

class ResumeProfile(BaseModel):
    candidate_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_designation: Optional[str] = None
    summary: Optional[str] = None

    education: List[EducationEntry] = Field(default_factory=list)
    experience: ExperienceBreakdown = Field(default_factory=ExperienceBreakdown)
    employment: List[EmploymentEntry] = Field(default_factory=list)
    research: ResearchProfile = Field(default_factory=ResearchProfile)

    certifications: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    courses_taught: List[CourseTaughtEntry] = Field(default_factory=list)
    teaching_interests: List[str] = Field(default_factory=list)
    academic_links: List[AcademicLink] = Field(default_factory=list)
    supervision: SupervisionSummary = Field(default_factory=SupervisionSummary)
    academic_service: List[str] = Field(default_factory=list)
    notable_highlights: List[NotableHighlight] = Field(default_factory=list)
    external_verification: Optional[ExternalVerification] = None
    projects: List[Dict[str, Any]] = Field(default_factory=list)

    screening: ScreeningResult = Field(default_factory=ScreeningResult)
    source_evidence: List[SourceEvidence] = Field(default_factory=list)
    metadata: Optional[ProcessingMetadata] = None

    # Review status tracking
    review_status: str = "Automatically processed"  # Automatically processed, High confidence, Needs review, Manually verified, Disqualified
    review_notes: Optional[str] = None
    reviewer_verdict: Optional[str] = None
