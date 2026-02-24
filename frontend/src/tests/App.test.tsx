import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import App from "../App"

// Mock WebSocket
vi.stubGlobal("WebSocket", vi.fn().mockImplementation(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  close: vi.fn(),
  readyState: 3,
})))

// Mock fetch for initial load
vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve([]),
}))

describe("App", () => {
  it("renders without crashing", () => {
    render(<App />)
    // App should render - check for any element
    expect(document.querySelector(".flex")).toBeTruthy()
  })

  it("shows disconnected status initially", () => {
    render(<App />)
    expect(screen.getByText("Disconnected")).toBeTruthy()
  })

  it("renders Settings button", () => {
    render(<App />)
    expect(screen.getByText("Settings")).toBeTruthy()
  })

  it("renders Prompts button", () => {
    render(<App />)
    expect(screen.getByText("Prompts")).toBeTruthy()
  })
})
