import { describe, it, expect } from "vitest"
import { taskCreateSchema, settingsSchema, questionSchema } from "../schemas/task"

describe("taskCreateSchema", () => {
  it("validates valid input", () => {
    const result = taskCreateSchema.safeParse({
      job_description: "Software Engineer at Acme Corp",
    })
    expect(result.success).toBe(true)
  })

  it("rejects empty job description", () => {
    const result = taskCreateSchema.safeParse({
      job_description: "",
    })
    expect(result.success).toBe(false)
  })

  it("applies defaults", () => {
    const result = taskCreateSchema.parse({
      job_description: "Test JD",
    })
    expect(result.generate_cover_letter).toBe(true)
    expect(result.template_id).toBe("classic")
    expect(result.language).toBe("en")
  })

  it("validates language enum", () => {
    const valid = taskCreateSchema.safeParse({
      job_description: "Test",
      language: "en",
    })
    expect(valid.success).toBe(true)

    const invalid = taskCreateSchema.safeParse({
      job_description: "Test",
      language: "fr",
    })
    expect(invalid.success).toBe(false)
  })
})

describe("questionSchema", () => {
  it("validates valid input", () => {
    const result = questionSchema.safeParse({
      question: "Why do you want to work here?",
      word_limit: 200,
    })
    expect(result.success).toBe(true)
  })

  it("rejects empty question", () => {
    const result = questionSchema.safeParse({
      question: "",
    })
    expect(result.success).toBe(false)
  })

  it("rejects word limit out of range", () => {
    const tooSmall = questionSchema.safeParse({
      question: "Test?",
      word_limit: 10,
    })
    expect(tooSmall.success).toBe(false)

    const tooBig = questionSchema.safeParse({
      question: "Test?",
      word_limit: 5000,
    })
    expect(tooBig.success).toBe(false)
  })
})

describe("settingsSchema", () => {
  it("validates partial settings", () => {
    const result = settingsSchema.safeParse({
      gemini_model: "gemini-3-pro-preview",
      max_latex_retries: 5,
    })
    expect(result.success).toBe(true)
  })

  it("validates empty object", () => {
    const result = settingsSchema.safeParse({})
    expect(result.success).toBe(true)
  })

  it("rejects invalid temperature", () => {
    const result = settingsSchema.safeParse({
      gemini_temperature: 5,
    })
    expect(result.success).toBe(false)
  })
})
