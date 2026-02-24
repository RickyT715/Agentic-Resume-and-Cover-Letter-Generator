# Agentic Resume & Cover Letter Generator

An AI-powered system that generates tailored resumes, cover letters, and application question answers using multiple LLM providers. Built with a FastAPI backend and a modern React frontend with real-time progress tracking.

## Features

### Multi-Provider AI Support
- **Google Gemini** — Gemini 2.0 Flash, Gemini 3 Pro, Gemini 3.1 Pro with configurable thinking levels (Minimal / Low / Medium / High)
- **Anthropic Claude** — Claude Sonnet 4.5, Claude Opus 4.6 via direct API
- **Claude Code Proxy** — Claude models via local proxy with SSE streaming
- **OpenAI-Compatible** — Any OpenAI-compatible API (Ollama, LM Studio, vLLM, etc.)
- Per-task provider override or global default

### Resume & Cover Letter Generation
- AI-generated LaTeX resumes tailored to each job description
- Professional cover letters with resume context awareness
- Page length validation (auto-regenerates if exceeding 1 page)
- Smart LaTeX compilation with error feedback and retry
- Multiple resume templates (Classic, Modern, Minimal)
- Bilingual support (English / Chinese)

### Application Questions
- Add per-task application questions with configurable word limits
- AI-generated answers grounded in your resume and the job description
- Generate answers individually or all at once
- Dedicated **Generated Answers** panel with per-answer and bulk copy
- Edit, delete, and regenerate questions at any time

### Task Management
- Multi-task support with concurrent generation (semaphore-limited)
- Task persistence across server restarts (JSON-backed)
- Real-time WebSocket progress updates per step
- Task retry, cancel, and delete
- Job description history for quick reuse
- Company name auto-extraction for file naming

### UI & Settings
- Dark mode with localStorage persistence
- Editable prompt templates with placeholder validation warnings
- Full settings panel: API keys, model selection, generation parameters
- PDF preview (inline iframe), LaTeX source download
- Keyboard shortcuts: `Ctrl+N` (new task), `Ctrl+Enter` (start), `Ctrl+S` (save settings), `Escape` (close modals)
- Toast notifications for all operations

## Architecture

```
┌─────────────────────┐     WebSocket      ┌─────────────────────┐
│    React Frontend    │◄──────────────────►│   FastAPI Backend   │
│  Zustand + Tailwind  │     REST API       │  Provider Registry  │
└─────────────────────┘                    └──────────┬──────────┘
                                                      │
                                        ┌─────────────┼─────────────┐
                                        │             │             │
                                   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
                                   │ Gemini  │  │ Claude  │  │ OpenAI  │
                                   │   API   │  │   API   │  │ Compat  │
                                   └─────────┘  └─────────┘  └─────────┘
                                                      │
                                           ┌──────────▼──────────┐
                                           │   LaTeX Compiler    │
                                           │   PDF Generation    │
                                           └─────────────────────┘
```

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **LaTeX** (MiKTeX on Windows, TeX Live on Linux/Mac)
- At least one API key: [Google AI Studio](https://aistudio.google.com/), [Anthropic](https://console.anthropic.com/), or a local proxy

## Quick Start (Windows)

1. **Run the installer:** double-click `install.bat`
2. **Configure your API key:** edit `backend/.env` (or configure later in the Settings UI)
3. **Start the application:** double-click `start.bat`

The app opens at **http://localhost:5173**.

## Manual Installation

### 1. System Dependencies

**Windows:** Install [MiKTeX](https://miktex.org/) — set "Install missing packages on-the-fly" to **Always**.

**Ubuntu/Debian:**
```bash
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**macOS:**
```bash
brew install --cask mactex
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API key(s)
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Running

**Backend** (terminal 1):
```bash
cd backend && python main.py
```

**Frontend** (terminal 2):
```bash
cd frontend && npm run dev
```

Open **http://localhost:5173**.

## Usage

1. **Create a Task** — click "New Task" in the sidebar (`Ctrl+N`)
2. **Paste Job Description** — paste the full JD into the text area
3. **Choose Options** — select template, language, provider, and toggle cover letter
4. **Add Application Questions** (optional) — type questions and set word limits
5. **Start** — click "Start Task" (`Ctrl+Enter`)
6. **Monitor** — watch real-time step-by-step progress
7. **Download** — grab the PDF, preview inline, or download LaTeX source
8. **Copy Answers** — use the Generated Answers panel to copy individual or all answers

## Configuration

All settings are configurable from the **Settings** panel in the UI and persisted to `backend/settings.json`.

### AI Providers

| Provider | Config Keys | Notes |
|----------|-------------|-------|
| Google Gemini | `gemini_api_key`, `gemini_model` | Supports thinking levels, Google Search grounding |
| Anthropic Claude | `claude_api_key`, `claude_model` | Direct Anthropic API |
| Claude Code Proxy | `claude_proxy_base_url`, `claude_proxy_model` | Uses SSE streaming to avoid response truncation |
| OpenAI-Compatible | `openai_compat_api_key`, `openai_compat_base_url`, `openai_compat_model` | Works with any OpenAI-compatible endpoint |

### Generation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Temperature | `1.0` | Creativity (0.0–2.0) |
| Max Output Tokens | Model default | Maximum response length |
| Thinking Level | `high` | Gemini 3+ reasoning depth: minimal, low, medium, high |
| Google Search | `false` | Web search grounding for company research |
| Max LaTeX Retries | `3` | Auto-retry LaTeX compilation on errors |

### Prompt Templates

Edit via the **Prompts** panel in the UI or directly in `backend/prompts/`:

| File | Description |
|------|-------------|
| `User_information_prompts.txt` | Your personal info (education, experience, skills) |
| `Resume_format_prompts.txt` | LaTeX template structure |
| `Resume_prompts.txt` | Main resume generation prompt |
| `Cover_letter_prompt.txt` | Cover letter generation prompt |
| `Application_question_prompt.txt` | Application question answering prompt |

**Placeholders** (auto-substituted):
- `{{user_information}}` — your personal info
- `{{latex_template}}` — LaTeX template content
- `{{JOB_DESCRIPTION}}` — the job description you provide

## API Reference

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tasks` | Create a new task |
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/{id}` | Get task details |
| `PUT` | `/api/tasks/{id}/settings` | Update task settings |
| `POST` | `/api/tasks/{id}/start` | Start processing |
| `POST` | `/api/tasks/{id}/retry` | Retry a failed/completed task |
| `POST` | `/api/tasks/{id}/cancel` | Cancel a running task |
| `DELETE` | `/api/tasks/{id}` | Delete a task |
| `DELETE` | `/api/tasks` | Clear completed tasks |
| `GET` | `/api/tasks/{id}/resume` | Download resume PDF |
| `GET` | `/api/tasks/{id}/cover-letter` | Download cover letter PDF |
| `GET` | `/api/tasks/{id}/latex` | Download LaTeX source |

### Application Questions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks/{id}/questions` | List questions for a task |
| `POST` | `/api/tasks/{id}/questions` | Add a question |
| `PUT` | `/api/tasks/{id}/questions/{qid}` | Update a question |
| `DELETE` | `/api/tasks/{id}/questions/{qid}` | Delete a question |
| `POST` | `/api/tasks/{id}/questions/{qid}/generate` | Generate answer for one question |
| `POST` | `/api/tasks/{id}/questions/generate-all` | Generate answers for all unanswered |

### Settings & Prompts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/settings` | Get all settings |
| `PUT` | `/api/settings` | Update settings |
| `POST` | `/api/settings/reset` | Reset to defaults |
| `GET` | `/api/prompts` | Get all prompts |
| `PUT` | `/api/prompts/{key}` | Update a prompt |
| `GET` | `/api/providers` | List available AI providers |
| `GET` | `/api/templates` | List resume templates |
| `GET` | `/api/jd-history` | Get job description history |
| `WS` | `/ws` | WebSocket for real-time updates |

## Project Structure

```
backend/
├── api/routes.py              # All REST + WebSocket endpoints
├── config.py                  # Pydantic settings from .env
├── main.py                    # FastAPI app with lifespan
├── models/task.py             # Pydantic models (Task, ApplicationQuestion, etc.)
├── services/
│   ├── ai_client_base.py      # Abstract base class for AI providers
│   ├── provider_registry.py   # Provider factory and caching
│   ├── gemini_client.py       # Google Gemini provider
│   ├── claude_client.py       # Anthropic Claude provider
│   ├── claude_proxy_client.py # Claude Code Proxy provider (SSE streaming)
│   ├── openai_compat_client.py# OpenAI-compatible provider
│   ├── task_manager.py        # Task orchestration and persistence
│   ├── prompt_manager.py      # Prompt loading and substitution
│   ├── settings_manager.py    # Settings persistence (JSON)
│   ├── latex_compiler.py      # LaTeX to PDF compilation
│   └── pdf_page_counter.py    # Page count validation
├── prompts/                   # Prompt template files
├── templates/                 # Resume style templates (classic, modern, minimal)
├── data/                      # Persisted tasks and JD history (gitignored)
├── output/                    # Generated PDFs (gitignored)
├── responses/                 # Saved API responses (gitignored)
└── tests/                     # pytest test suite

frontend/
├── src/
│   ├── components/
│   │   ├── TaskPanel.tsx      # Main task UI + Generated Answers panel
│   │   ├── TaskSidebar.tsx    # Task list sidebar
│   │   ├── QuestionsSection.tsx # Application questions CRUD
│   │   ├── SettingsPanel.tsx  # Settings modal (all providers)
│   │   ├── PromptsPanel.tsx   # Prompt template editor
│   │   ├── ProgressDisplay.tsx# Real-time step progress
│   │   └── ToastContainer.tsx # Toast notifications
│   ├── store/taskStore.ts     # Zustand state management
│   ├── hooks/useWebSocket.ts  # WebSocket hook
│   └── types/task.ts          # TypeScript type definitions
├── package.json
└── vite.config.ts
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `pdflatex not found` | Install MiKTeX (Windows) or texlive (Linux/Mac) |
| `pdflatex timed out` | Open MiKTeX Console, set "Install missing packages" to "Always" |
| WebSocket connection failed | Ensure backend is running on port 8000 |
| `Errno 10048: port already in use` | Kill the existing process: find PID with `netstat -ano \| findstr :8000`, then `taskkill /PID <pid> /F` |
| Proxy response truncation | The Claude Code Proxy client uses SSE streaming by default to avoid this |
| `Thinking level not supported` | Use a Gemini 3+ model (e.g., `gemini-3.1-pro-preview`) |

## License

MIT License
