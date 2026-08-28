/**
 * Centralized TypeScript type definitions for Echo Apply Frontend.
 */

export interface EducationItem {
  degree: string;
  major?: string;
  school: string;
  date: string;
  gpa?: string;
}

export interface ExperienceItem {
  role: string;
  company: string;
  start_date: string;
  end_date?: string;
  location?: string;
  bullets: string[];
}

export interface ProjectItem {
  name: string;
  link?: string;
  bullets: string[];
}

export interface HighlightStripItem {
  skill: string;
  relevance_reason: string;
}

export interface ResumeParsedData {
  name: string;
  email: string;
  phone?: string;
  location?: string;
  links: string[];
  skills: string[];
  education: EducationItem[];
  experience: ExperienceItem[];
  projects: ProjectItem[];
  anchor_line?: string;
  highlights_strip?: HighlightStripItem[];
  color_theme?: Record<string, string>;
  font_family?: string;
  executive_summary?: string;
  certifications?: string[];
  languages?: string[];
  scroll_stop_hook?: string;
}

export interface TopRepository {
  name: string;
  description?: string;
  language?: string;
  stars: number;
  url: string;
}

export interface GitHubEnrichedData {
  username: string;
  total_stars: number;
  languages: Record<string, number>;
  top_repositories: TopRepository[];
}

export interface IntakeResult {
  user_id: string;
  parsed_resume: ResumeParsedData;
  github_enriched: GitHubEnrichedData | null;
}

export interface JobCard {
  job_id: string;
  source: string;
  title: string;
  company: string;
  location?: string;
  remote: boolean;
  apply_url?: string;
  jd_text: string;
  fetched_at: string;
  job_hash: string;
  match_score?: number;
  match_explanation?: string;
  is_applied: boolean;
}

export interface ScreenQuestionDraft {
  question_id: string;
  question_text: string;
  drafted_answer: string;
  confidence: number;
  needs_user_input: boolean;
  warning_message?: string;
}

export interface ApplicationQuality {
  overall: number;
  resume_match: number;
  required_skills: number;
  experience_fit: number;
  keyword_coverage: number;
  factual_confidence: number;
  cover_letter: number;
  missing_requirements: string[];
  fix_suggestions: string[];
}

export interface SavedAlert {
  id: string;
  keywords: string;
  location: string | null;
  alert_interval: string;
  created_at: string;
}

export interface BulletVerification {
  rewritten_bullet: string;
  is_fabricated: boolean;
  justification: string;
  suggested_fix?: string;
}

export interface TruthfulnessReport {
  is_fabricated: boolean;
  verification_report: BulletVerification[];
}

export interface GapAnalysis {
  matched_skills: string[];
  missing_skills: string[];
  partial_matches?: string[];
}
