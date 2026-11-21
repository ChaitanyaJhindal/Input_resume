export interface EducationEntry {
  degree: string;
  normalized_degree: string;
  field?: string | null;
  institution: string;
  institution_normalized?: string | null;
  institution_category?: string | null;
  institution_tier?: string | null;
  graduation_year?: number | null;
  confidence: number;
  evidence?: string | null;
  source_page?: number;
}

export interface EmploymentEntry {
  title: string;
  organization: string;
  category: 'teaching' | 'research' | 'industry' | 'administrative' | string;
  start_date?: string | null;
  end_date?: string | null;
  duration_years: number;
  is_current?: boolean;
  description?: string | null;
  evidence?: string | null;
}

export interface ExperienceBreakdown {
  total_years: number;
  teaching_years: number;
  research_years: number;
  industry_years: number;
  administrative_years: number;
}

export interface PublicationEntry {
  title: string;
  venue?: string | null;
  year?: number | null;
  doi?: string | null;
  indexed?: string | null;
  evidence?: string | null;
}

export interface ResearchProfile {
  publications: PublicationEntry[];
  patents: any[];
  research_projects: any[];
  research_domains: string[];
  books?: any[];
}

export interface RuleEvaluation {
  rule_id: string;
  name: string;
  status: 'pass' | 'fail' | 'unknown';
  reason: string;
  evidence?: string | null;
  confidence: number;
  is_mandatory: boolean;
  weight: number;
}

export interface ScreeningResult {
  eligibility_status: 'eligible' | 'needs_review' | 'disqualified' | string;
  overall_score: number;
  confidence: number;
  flags: string[];
  rules_evaluated: RuleEvaluation[];
  decision_path?: string[];
}

export interface SourceEvidence {
  field: string;
  value: any;
  evidence: string;
  source_page?: number;
  confidence: number;
}

export interface ProcessingMetadata {
  pipeline_version: string;
  model_name: string;
  file_name: string;
  file_path: string;
  file_hash: string;
  page_count: number;
  processing_time_seconds: number;
  groq_api_calls: number;
  jev_decision_calls: number;
  deterministic_resolutions: number;
  processed_at: string;
}

export interface Candidate {
  id: string;
  candidate_id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  current_designation?: string | null;
  summary?: string | null;

  highest_degree?: string | null;
  highest_institution?: string | null;
  highest_institution_category?: string | null;
  institution_tier?: string | null;

  teaching_years: number;
  research_years: number;
  industry_years: number;
  total_years: number;
  publications_count: number;

  eligibility_status: 'eligible' | 'needs_review' | 'disqualified' | string;
  overall_score: number;
  confidence: number;
  review_status: string;
  review_notes?: string | null;
  reviewer_verdict?: string | null;

  file_name: string;
  file_path: string;
  is_uploaded?: boolean;
  updated_at?: string | null;

  education: EducationEntry[];
  employment: EmploymentEntry[];
  publications: PublicationEntry[];
  rules_evaluated: RuleEvaluation[];
  source_evidence?: SourceEvidence[];
  research?: ResearchProfile;
  skills?: string[];
  certifications?: string[];
  awards?: string[];
  metadata?: ProcessingMetadata;
}

export interface AnalyticsMetrics {
  total_resumes: number;
  processed: number;
  eligible: number;
  needs_review: number;
  disqualified: number;
  average_teaching_years: number;
  average_processing_time_sec: number;
}

export interface AnalyticsOverview {
  metrics: AnalyticsMetrics;
  distributions: {
    degree: { name: string; count: number }[];
    institution_category: { name: string; count: number }[];
    experience: { bracket: string; count: number }[];
  };
  telemetry: {
    deterministic_resolutions: number;
    jev_decision_calls: number;
    groq_api_calls: number;
    escalations: number;
    total_latency_ms: number;
  };
}

export interface ScreeningRuleConfig {
  id: string;
  name: string;
  description: string;
  field: string;
  operator: string;
  required_value: any;
  is_mandatory: boolean;
  weight: number;
  failure_message: string;
}
