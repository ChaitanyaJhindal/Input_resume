export type EligibilityStatus = "eligible" | "needs_review" | "disqualified";

export type ReviewStatus =
  | "Automatically processed"
  | "High confidence"
  | "Needs review"
  | "Manually verified"
  | "Disqualified";

export interface EducationEntry {
  degree: string;
  normalized_degree: string;
  field?: string | null;
  institution: string;
  institution_normalized?: string | null;
  institution_category?: string | null;
  institution_tier?: string | null;
  start_year?: number | null;
  graduation_year?: number | null;
  thesis_title?: string | null;
  advisor?: string | null;
  gpa_or_honors?: string | null;
  status?: string;
  confidence: number;
  evidence?: string | null;
  source_page?: number | null;
}

export interface CourseTaughtEntry {
  course_name: string;
  course_code?: string | null;
  level: string;
  institution?: string | null;
  term_or_years?: string | null;
  role: string;
  evidence?: string | null;
  source_page?: number | null;
}

export interface AcademicLink {
  platform: string;
  url: string;
  identifier?: string | null;
  source: string;
  verified: boolean;
}

export interface SupervisionSummary {
  phd_completed: number;
  phd_ongoing: number;
  masters_guided: number;
  ug_projects_guided: number;
  details: string[];
}

export interface NotableHighlight {
  category: string;
  title: string;
  impact?: string | null;
  evidence?: string | null;
}

export interface ExternalVerification {
  orcid_verified: boolean;
  openalex_id?: string | null;
  citation_count?: number | null;
  h_index?: number | null;
  i10_index?: number | null;
  works_count?: number | null;
  match_method: string;
  verified_at?: string | null;
  source_url?: string | null;
  notes?: string | null;
}

export interface EmploymentEntry {
  title: string;
  organization: string;
  category: string;
  start_date?: string | null;
  end_date?: string | null;
  duration_years: number;
  is_current: boolean;
  description?: string | null;
  evidence?: string | null;
  source_page?: number | null;
}

export interface PublicationEntry {
  title: string;
  venue?: string | null;
  year?: number | null;
  doi?: string | null;
  citation_count?: number | null;
  indexed?: string | null;
  evidence?: string | null;
}

export interface ResearchProjectEntry {
  title?: string;
  role?: string;
  sponsor?: string;
  agency?: string;
  year?: number | string;
  amount?: string;
  status?: string;
}

export interface ProjectEntry {
  title?: string;
  name?: string;
  description?: string;
  technologies?: string[];
  year?: number | string;
}

export interface ResearchProfile {
  publications: PublicationEntry[];
  patents: Array<Record<string, unknown>>;
  research_projects: ResearchProjectEntry[];
  research_domains: string[];
  books: Array<Record<string, unknown>>;
}

export interface RuleEvaluation {
  rule_id: string;
  name: string;
  status: "pass" | "fail" | "unknown";
  reason: string;
  evidence?: string | null;
  confidence: number;
  is_mandatory: boolean;
  weight: number;
}

export interface SourceEvidence {
  field: string;
  value: unknown;
  evidence: string;
  source_page?: number | null;
  confidence: number;
  position_available?: boolean;
  bounding_box?: number[] | null;
}

export interface CandidateMetadata {
  pipeline_version?: string;
  model_name?: string;
  file_name?: string;
  file_path?: string;
  file_hash?: string;
  page_count?: number;
  processing_time_seconds?: number;
  groq_api_calls?: number;
  jev_decision_calls?: number;
  deterministic_resolutions?: number;
  escalations?: number;
  grounding_score?: number;
  extraction_method?: string;
  json_repaired?: boolean;
  processed_at?: string;
}

export interface Candidate {
  id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  current_designation?: string | null;
  summary?: string | null;
  highest_degree: string;
  highest_institution: string;
  highest_institution_category: string;
  teaching_years: number;
  research_years: number;
  industry_years: number;
  administrative_years?: number;
  total_years: number;
  publications_count: number;
  eligibility_status: EligibilityStatus;
  overall_score: number;
  confidence: number;
  grounding_score?: number | null;
  processing_time_seconds?: number | null;
  page_count?: number | null;
  review_status: string;
  review_notes?: string | null;
  reviewer_verdict?: string | null;
  file_name: string;
  file_path: string;
  is_uploaded: boolean;
  processed_at?: string | null;
  education: EducationEntry[];
  employment: EmploymentEntry[];
  publications: PublicationEntry[];
  research?: ResearchProfile;
  skills?: string[];
  awards?: string[];
  certifications?: string[];
  courses_taught?: CourseTaughtEntry[];
  courses_taught_count?: number;
  teaching_interests?: string[];
  supervision?: SupervisionSummary;
  academic_service?: string[];
  notable_highlights?: NotableHighlight[];
  academic_links?: AcademicLink[];
  external_verification?: ExternalVerification | null;
  has_google_scholar?: boolean;
  has_orcid?: boolean;
  external_citations?: number | null;
  external_h_index?: number | null;
  projects?: ProjectEntry[];
  rules_evaluated: RuleEvaluation[];
  screening_flags?: string[];
  decision_path?: string[];
  source_evidence?: SourceEvidence[];
  metadata?: CandidateMetadata | null;
  review_reasons?: string[];
  jd_evaluation?: CandidateJDEvaluation | null;
}

export type RecommendationTier =
  | "strong_match"
  | "strong_alternative_fit"
  | "conditional_review"
  | "low_alignment";

export type JDApprovalStatus =
  | "pending"
  | "approved"
  | "approved_alternative"
  | "interview_recommended"
  | "hold"
  | "rejected";

export interface JDRequirement {
  id: string;
  category: string;
  label: string;
  priority: "must_have" | "strong_preference" | "nice_to_have";
  weight: number;
  strictness: "strict" | "flexible_with_equivalence";
  jd_quote?: string | null;
}

export interface JDWeights {
  requirement_fit: number;
  domain_semantic_fit: number;
  teaching_fit: number;
  research_and_impact: number;
  alternative_strength_credit: number;
}

export interface JobDescription {
  jd_id: string;
  title: string;
  department?: string | null;
  level?: string | null;
  role_archetype: string;
  summary?: string | null;
  raw_text?: string;
  file_name?: string | null;
  is_active?: boolean;
  evaluated_count?: number;
  requirements: JDRequirement[];
  required_domains: string[];
  preferred_courses: string[];
  research_expectations?: string | null;
  industry_practice_value?: string | null;
  allow_compensating_strengths: boolean;
  weights: JDWeights;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RequirementMatch {
  requirement_id: string;
  label: string;
  category: string;
  priority: string;
  status: "met" | "partially_met" | "compensated" | "gap";
  score: number;
  evidence?: string | null;
  rationale: string;
}

export interface CompensatingStrength {
  missed_requirement: string;
  compensating_evidence: string;
  rationale: string;
  strength_level: "strong" | "moderate";
}

export interface DimensionScores {
  requirement_fit: number;
  domain_semantic_fit: number;
  teaching_fit: number;
  research_and_impact: number;
  alternative_strength_credit: number;
}

export interface CandidateJDEvaluation {
  jd_id: string;
  candidate_id: string;
  dynamic_score: number;
  recommendation_tier: RecommendationTier;
  confidence: number;
  grounding_score: number;
  dimension_scores: DimensionScores;
  requirement_matrix: RequirementMatch[];
  compensating_strengths: CompensatingStrength[];
  standout_highlights: NotableHighlight[];
  executive_brief: string;
  interview_probes: string[];
  approval_status: JDApprovalStatus;
  approval_notes?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  evaluated_at?: string | null;
}

export interface JDCandidatesSummary {
  total_evaluated: number;
  strong_match: number;
  strong_alternative_fit: number;
  conditional_review: number;
  low_alignment: number;
  approved_count: number;
}

export interface JDEvaluateStatus {
  running: boolean;
  total: number;
  completed: number;
  failed: number;
  current_candidate: string | null;
  last_error: string | null;
}

export interface RulePassRate {
  rule_id: string;
  name: string;
  passed: number;
  failed: number;
  total: number;
  pass_rate_pct: number;
  is_mandatory: boolean;
}

export interface GroqKeyStat {
  key_index: number;
  requests: number;
  cooling_down: boolean;
}

export interface GroqPoolTelemetry {
  total_keys: number;
  active_available_keys: number;
  rotations_handled: number;
  key_distribution: GroqKeyStat[];
}

export interface AnalyticsOverview {
  metrics: {
    total_resumes: number;
    source_resumes: number;
    uploaded_resumes: number;
    processed: number;
    eligible: number;
    needs_review: number;
    disqualified: number;
    average_teaching_years: number;
    average_processing_time_sec: number;
  };
  distributions: {
    degree: Array<{ name: string; count: number }>;
    institution_category: Array<{ name: string; count: number }>;
    experience: Array<{ bracket: string; count: number }>;
    rule_pass_rates: RulePassRate[];
    score_brackets: Array<{ bracket: string; count: number }>;
    grounding_brackets: Array<{ bracket: string; count: number }>;
  };
  telemetry: {
    deterministic_resolutions: number;
    jev_decision_calls: number;
    groq_api_calls: number;
    escalations: number;
    total_latency_ms: number;
  };
  groq_pool?: GroqPoolTelemetry;
}

export interface SyncStatus {
  running: boolean;
  total: number;
  completed: number;
  failed: number;
  current_file: string | null;
  started_at: string | null;
  finished_at: string | null;
  last_error: string | null;
}

export interface ScreeningRuleConfig {
  id: string;
  name: string;
  description?: string;
  field: string;
  operator: string;
  required_value: string | number | boolean | string[];
  is_mandatory: boolean;
  weight: number;
  failure_message?: string;
}

export interface ScreeningRulesResponse {
  version?: string;
  department?: string;
  academic_year?: string;
  rules: ScreeningRuleConfig[];
  settings: {
    overall_passing_score_percentage: number;
    minimum_confidence_for_auto_approval: number;
    needs_review_confidence_floor: number;
  };
}

export interface LlmTaskOverride {
  model?: string;
  temperature?: number | null;
  max_tokens?: number | null;
  reasoning_format?: string | null;
  reasoning_effort?: string | null;
  top_p?: number | null;
  min_text_chars?: number;
  max_text_chars?: number;
  max_pages?: number;
  render_scale?: number;
  thumbnail_size?: number[];
  image_quality?: number;
  escalation_confidence_threshold?: number;
}

export interface LlmConfigData {
  groq?: {
    models?: Record<string, string>;
    defaults?: {
      max_tokens?: number;
      temperature?: number;
    };
    pool?: {
      cooldown_seconds?: number;
      max_cooldown_wait_seconds?: number;
      max_retries?: number;
      pacing_delay_seconds?: number;
      client_max_retries?: number;
      request_timeout_seconds?: number;
    };
  };
  jev?: {
    model?: string;
    base_url?: string;
    timeout_seconds?: number;
    confidence_threshold?: number;
  };
  tasks?: Record<string, LlmTaskOverride>;
}

export interface LlmConfigResponse {
  config: LlmConfigData;
  resolved_models: Record<string, string>;
  groq_models: Record<string, string>;
}

export type PromptTemplateEntry = Record<string, string>;

export interface PromptsConfigResponse {
  prompts: Record<string, PromptTemplateEntry>;
}

export interface AppConfigData {
  app_name?: string;
  version?: string;
  taxonomy?: {
    degree_levels?: string[];
    institution_categories?: string[];
    institution_tiers?: string[];
    experience_categories?: string[];
  };
  pipeline?: {
    version?: string;
    agentic_version?: string;
    vision_scale?: number;
    image_quality?: number;
    max_pages_per_resume?: number;
    cache_processed_results?: boolean;
    hash_algorithm?: string;
    supported_extensions?: string[];
    ignored_directories?: string[];
    batch_upload_delay_seconds?: number;
    max_upload_size_mb?: number;
  };
  review?: {
    high_confidence_threshold?: number;
    queue_confidence_threshold?: number;
    queue_min_teaching_years?: number;
  };
  export?: Record<string, string>;
}

export interface SystemStatus {
  environment: string;
  mock_mode: boolean;
  groq_vision_model: string;
  groq_reasoning_model: string;
  groq_advanced_model: string;
  groq_configured: boolean;
  groq_keys_count: number;
  typesafe_jev_model: string;
  typesafe_configured: boolean;
  resumes_directory: string;
  database: string;
  resolved_task_models: Record<string, string>;
}

export interface ResumeResultResponse {
  candidate_id: string;
  profile: Record<string, unknown>;
  markdown: string;
}
