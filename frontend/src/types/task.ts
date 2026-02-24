export type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'skipped';

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
  provider?: string | null;
  steps: StepProgress[];
  resume_pdf_path?: string;
  cover_letter_pdf_path?: string;
  latex_source?: string;
  error_message?: string;
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
