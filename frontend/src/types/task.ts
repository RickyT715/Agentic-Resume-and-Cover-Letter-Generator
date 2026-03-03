export type TaskStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'skipped';

export type QuestionStatus = 'pending' | 'running' | 'completed' | 'failed';

export type AIProvider = 'gemini' | 'claude' | 'openai_compat';

export interface ProviderInfo {
  id: string;
  name: string;
  description: string;
}

export interface ApplicationQuestion {
  id: string;
  question: string;
  word_limit: number;
  answer?: string;
  status: QuestionStatus;
  error_message?: string;
  created_at: string;
  answered_at?: string;
}

export type TaskStep =
  | 'generate_resume'
  | 'compile_latex'
  | 'extract_text'
  | 'generate_cover_letter'
  | 'create_cover_pdf';

export interface StepProgress {
  step: TaskStep;
  status: TaskStatus;
  message: string;
  attempt: number;
  started_at?: string;
  completed_at?: string;
}

export interface Task {
  id: string;
  task_number: number;
  job_description: string;
  status: TaskStatus;
  generate_cover_letter: boolean;
  template_id: string;
  language?: string;
  experience_level?: string;
  provider?: string | null;
  pipeline_version?: string;
  steps: StepProgress[];
  resume_pdf_path?: string;
  cover_letter_pdf_path?: string;
  latex_source?: string;
  error_message?: string;
  validation_warnings?: string[];
  company_name?: string;
  position_name?: string;
  questions?: ApplicationQuestion[];
  cancelled?: boolean;
  created_at: string;
  completed_at?: string;
}

export interface ProgressUpdate {
  task_id: string;
  task_number: number;
  step: TaskStep;
  status: TaskStatus;
  message: string;
  attempt: number;
  node?: string;
  pipeline_version?: string;
}

export interface WebSocketMessage {
  type: 'progress';
  data: ProgressUpdate;
}

export interface Template {
  id: string;
  name: string;
  description: string;
}

export interface JDHistoryEntry {
  text: string;
  preview: string;
  saved_at: string;
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

export interface AppSettings {
  default_provider: string;
  gemini_api_key: string;
  gemini_model: string;
  gemini_temperature: number | null;
  gemini_top_k: number | null;
  gemini_top_p: number | null;
  gemini_max_output_tokens: number | null;
  gemini_thinking_level: string;
  gemini_enable_search: boolean;
  claude_api_key: string;
  claude_model: string;
  claude_temperature: number | null;
  claude_max_output_tokens: number | null;
  claude_extended_thinking: boolean;
  claude_thinking_budget: number;
  openai_compat_base_url: string;
  openai_compat_api_key: string;
  openai_compat_model: string;
  openai_compat_temperature: number | null;
  openai_compat_max_output_tokens: number | null;
  claude_proxy_base_url: string;
  claude_proxy_api_key: string;
  claude_proxy_model: string;
  claude_proxy_temperature: number | null;
  claude_proxy_max_output_tokens: number | null;
  deepseek_api_key: string;
  deepseek_model: string;
  deepseek_temperature: number | null;
  deepseek_max_output_tokens: number | null;
  qwen_api_key: string;
  qwen_model: string;
  qwen_temperature: number | null;
  qwen_max_output_tokens: number | null;
  enforce_resume_one_page: boolean;
  enforce_cover_letter_one_page: boolean;
  max_page_retry_attempts: number;
  generate_cover_letter: boolean;
  max_latex_retries: number;
  default_template_id: string;
  default_experience_level: string;
  allow_ai_fabrication: boolean;
  enable_contact_replacement: boolean;
  enable_text_validation: boolean;
  enable_llm_validation: boolean;
  user_linkedin_url: string;
  user_github_url: string;
  agent_providers: Record<string, string>;
}

export interface EvaluationData {
  ats_score: number;
  ats_breakdown: {
    keyword_similarity: number;
    semantic_similarity: number;
    skill_coverage: number;
    fuzzy_match: number;
    resume_quality: number;
    section_bonus: number;
    action_verbs_score: number;
    quantified_score: number;
    section_score: number;
    format_score: number;
  };
  matched_keywords: string[];
  missing_keywords: string[];
  combined_score: number;
  passed: boolean;
  llm_score?: number | null;
  llm_breakdown?: {
    keyword_alignment: number;
    professional_tone: number;
    quantified_achievements: number;
    relevance: number;
    ats_compliance: number;
    reasoning: string;
    improvements: string[];
  } | null;
}

export type Prompts = Record<string, string>;
