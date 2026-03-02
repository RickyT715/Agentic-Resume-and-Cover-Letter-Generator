import { z } from "zod"

export const taskCreateSchema = z.object({
  job_description: z.string().min(1, "Job description is required"),
  generate_cover_letter: z.boolean().default(true),
  template_id: z.string().default("classic"),
  language: z.enum(["en", "zh"]).default("en"),
  experience_level: z.enum(["auto", "new_grad", "experienced"]).default("auto"),
  provider: z.string().optional(),
})

export type TaskCreateInput = z.infer<typeof taskCreateSchema>

export const taskSettingsSchema = z.object({
  job_description: z.string().optional(),
  generate_cover_letter: z.boolean().optional(),
  template_id: z.string().optional(),
  language: z.string().optional(),
  experience_level: z.string().optional(),
  provider: z.string().optional(),
})

export type TaskSettingsInput = z.infer<typeof taskSettingsSchema>

export const questionSchema = z.object({
  question: z.string().min(1, "Question is required"),
  word_limit: z.number().int().min(50).max(1000).default(150),
})

export type QuestionInput = z.infer<typeof questionSchema>

export const settingsSchema = z.object({
  default_provider: z.string().optional(),
  gemini_api_key: z.string().optional(),
  gemini_model: z.string().optional(),
  gemini_temperature: z.number().min(0).max(2).optional(),
  gemini_thinking_level: z.string().optional(),
  gemini_enable_search: z.boolean().optional(),
  claude_api_key: z.string().optional(),
  claude_model: z.string().optional(),
  openai_compat_base_url: z.string().url().optional().or(z.literal("")),
  openai_compat_api_key: z.string().optional(),
  openai_compat_model: z.string().optional(),
  enforce_resume_one_page: z.boolean().optional(),
  enforce_cover_letter_one_page: z.boolean().optional(),
  max_latex_retries: z.number().int().min(1).max(10).optional(),
  default_template_id: z.string().optional(),
})

export type SettingsInput = z.infer<typeof settingsSchema>
