# Agentic Resume & Cover Letter Generator

[中文文档](README_zh.md)

An AI-powered system that generates tailored resumes, cover letters, and application question answers using a **multi-agent LangGraph pipeline** with automated evaluation, company research (RAG), and multiple LLM providers. Built with FastAPI, React, and TypeScript.

## What's New in v3.2

- **ATS-Optimized Resume Format** — Redesigned LaTeX template based on research from 30+ sources (FAANG recruiter guides, ATS system docs, Google/Harvard/Stanford career services). Key improvements:
  - **Conditional layout** — Experienced (2+ yrs): Summary → Experience → Projects → Skills → Education. New grads: Education → Skills → Projects → Experience
  - **Summary section** — JD-targeted 1-2 sentence summary with years of experience, core domain, key technologies, and quantified highlight
  - **Structured Technical Skills** — 5 categories (Languages, Frameworks, Cloud & DevOps, Databases, Tools) with dual-form keywords
  - **X-Y-Z bullet formula** — "Accomplished [X] as measured by [Y] by doing [Z]" with 3-5 bullets per role guidance
  - **Standard section headers** — `Technical Skills` (replaces `Programming Skills`), ATS-recognized names across all sections
- **Enhanced Quality Checklist** — Both English and Chinese prompts now enforce Summary presence, categorized skills, 8+ distinct action verbs, and 5+ quantified achievements
- **Example Resume PDFs** — 3 reference PDFs in `backend/output/examples/` (new grad, experienced engineer, senior AI/ML)

### v3.1

- **Hybrid Multi-Method ATS Scorer** — 6 complementary scoring methods (BM25, semantic embeddings, skill coverage, fuzzy matching, quality heuristics, section-aware bonus) with sigmoid calibration and synonym normalization. See [ATS Scoring System](#ats-scoring-system) for details.
- **ATS-Optimized Prompts** — Resume generation prompt now instructs the AI to use dual-form keywords (e.g., "Machine Learning (ML)"), distribute keywords across multiple sections, and use standard ATS-recognized section headers.
- **Cover Letter Text Preview** — Copy-pasteable plain text view of cover letters (no line breaks from PDF rendering)
- **Task Cancellation** — Cancel running tasks mid-pipeline with partial result preservation
- **AI Expert Review Fix** — LLM-as-judge results now correctly cached and displayed

### v3.0

- **Multi-Agent Pipeline** — LangGraph StateGraph with JD analysis, relevance matching, quality-gated retries, and structured outputs
- **Automated Evaluation** — Hybrid ATS scoring + LLM-as-a-judge with self-critique feedback loop
- **Company Research (RAG)** — Scrape company websites, index in ChromaDB, inject relevant context into resume and cover letter generation
- **Modern Frontend** — shadcn/ui components, TanStack Query v5 for server state, Zod schema validation, ATS score visualizations, agent pipeline progress UI
- **Production Ready** — Docker multi-stage builds, PostgreSQL support, GitHub Actions CI/CD, rate limiting, security scanning

## Features

### Multi-Agent Pipeline (v3)

The v3 pipeline processes each resume through a sequence of specialized agents:

```
JD Analyzer → Relevance Matcher → [Company Research] → Resume Writer → Quality Gate
    ↻ retry if score < 0.7 (max 2)
    → LaTeX Compilation → [Cover Letter → Cover Letter PDF] → Finalize
```

- **JD Analyzer** — extracts job title, skills, experience level, responsibilities, and industry
- **Relevance Matcher** — matches your profile against JD requirements, identifies emphasis points
- **Company Research** (optional) — retrieves indexed company context from the RAG vector store
- **Resume Writer** — generates LaTeX resume with job-specific optimization instructions
- **Quality Gate** — ATS scoring with conditional retry routing (score < 0.7 triggers revision with feedback)
- **Cover Letter Writer** — generates cover letter informed by resume content, JD analysis, and company context
- The classic v2 pipeline (single AI call) remains available as a fallback

### Automated Evaluation

- **Hybrid ATS Scorer** — 6 complementary methods with research-backed weights (see [ATS Scoring System](#ats-scoring-system) below)
- **LLM-as-a-Judge** — 5-rubric evaluation: keyword alignment, professional tone, quantified achievements, relevance, ATS compliance + reasoning and improvement suggestions
- **Self-Critique Loop** — low scores generate actionable feedback that's appended to the retry prompt
- **Visual Dashboard** — score bars with collapsible quality details, matched/missing keyword badges, expert review display

### Company Research (RAG)

- Scrape company websites with rate limiting and robots.txt respect
- Chunk and embed content using sentence-transformers (or fallback embeddings)
- Index in ChromaDB with metadata (source type, company name, content type)
- **Corrective RAG** — retrieve → grade relevance → rewrite query if poor → retrieve again
- Company context automatically injected into resume and cover letter prompts
- 30-day cache with manual refresh

### Multi-Provider AI Support

- **Google Gemini** — Gemini 2.0 Flash, Gemini 3 Pro, Gemini 3.1 Pro with configurable thinking levels
- **Anthropic Claude** — Claude Sonnet 4.5, Claude Opus 4.6 via direct API
- **Claude Code Proxy** — Claude models via local proxy with SSE streaming
- **OpenAI-Compatible** — Any OpenAI-compatible API (Ollama, LM Studio, vLLM, etc.)
- **DeepSeek** — DeepSeek Chat/Reasoner via DeepSeek API
- **Qwen** — Qwen Plus/Max/Turbo via Alibaba DashScope API
- Per-task provider override or global default

### ATS Scoring System

The evaluation module uses a **hybrid multi-method ATS scorer** combining 6 complementary approaches, based on research into real ATS systems (Workday, iCIMS, Taleo) and open-source implementations. Each method captures a different aspect of resume-JD alignment:

| Method | Weight | Library | What It Measures |
|--------|--------|---------|------------------|
| **BM25 Keyword Relevance** | 20% | `rank-bm25` | Document-level keyword relevance with term frequency saturation and length normalization (superior to TF-IDF) |
| **Semantic Embedding Similarity** | 20% | `sentence-transformers` | Meaning beyond exact words — captures synonyms, paraphrases, and conceptual overlap |
| **Skill Coverage** | 30% | `spaCy` PhraseMatcher | Explicit skill overlap from a 550+ curated skill taxonomy across 15 categories |
| **Fuzzy Keyword Matching** | 10% | `rapidfuzz` | Catches abbreviations, typos, and variations (e.g., K8s → Kubernetes) |
| **Resume Quality Heuristics** | 10% | regex | Action verbs, quantified achievements, section completeness, format quality |
| **Section-Aware Bonus** | 10% | regex | Rewards keyword placement in high-impact sections (Skills 35%, Experience 30%, Summary 15%) |

**Key design decisions:**
- **BM25 over TF-IDF** — BM25Plus handles term frequency saturation (repeated words don't over-inflate scores) and document length normalization (fair comparison for different resume lengths)
- **Synonym normalization** — A pre-processing layer expands 60+ abbreviations (AWS → Amazon Web Services, ML → Machine Learning) so both forms are matched regardless of which appears in the JD or resume
- **Sigmoid calibration** — Raw similarity scores are mapped through a sigmoid curve rather than linear scaling, providing better discrimination in the typical 0.1–0.5 score range
- **Skill coverage weighted highest (30%)** — Research from commercial ATS tools (Jobscan, ResumeWorded) and HR studies consistently shows hard skill matching is the strongest predictor of interview callbacks
- **Section-aware scoring** — Real ATS systems weight the Skills section higher than body text; this method rewards resumes that distribute keywords across Summary, Skills, and Experience sections

**Scoring pipeline:**

```
Resume LaTeX → Text Extraction → Synonym Normalization →
  ├─ BM25 scoring (resume sentences as corpus, JD as query)
  ├─ Semantic embedding (chunked average cosine similarity)
  ├─ Skill coverage (PhraseMatcher + taxonomy + required skill weighting)
  ├─ Fuzzy matching (token_set_ratio against JD skills)
  ├─ Quality heuristics (action verbs, metrics, sections, format)
  └─ Section bonus (keyword density per LaTeX section, weighted by section importance)
  → Sigmoid calibration per method → Weighted sum → Overall score (0–1)
```

The skill taxonomy (`evaluation/skills_taxonomy.py`) contains 550+ skills organized into 15 categories: Programming Languages, Frontend, Backend, Databases, Cloud, DevOps, Data Science, Data Engineering, Security, Mobile, Testing, Architecture, Methodologies, Soft Skills, and Tools.

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

### Chinese Language Support

- Bilingual pipeline (English / Chinese) with language auto-detection
- Chinese JD analysis with dedicated prompt templates
- CJK font support in PDF generation (requires a CJK font such as Noto Sans CJK)
- Chinese skill taxonomy (action verbs, section names)
- `jieba` tokenization for Chinese text processing
- DeepSeek and Qwen providers optimized for Chinese content

### Task Management

- Multi-task support with concurrent generation (semaphore-limited)
- Task persistence across server restarts (JSON-backed + optional PostgreSQL)
- Real-time WebSocket progress updates per step
- Task retry, cancel, and delete
- Job description history for quick reuse

### Frontend

- Dark mode with localStorage persistence
- **shadcn/ui** component library (Button, Card, Badge, Progress)
- **TanStack Query v5** for server state with automatic caching and refetching
- **Zod** schema validation for forms
- Agent pipeline progress visualization (v3)
- ATS score breakdown charts with matched/missing skill badges
- PDF preview, LaTeX source download
- Keyboard shortcuts: `Ctrl+N` (new task), `Ctrl+Enter` (start), `Ctrl+S` (save settings), `Escape` (close modals)
- Toast notifications for all operations

## Architecture

```
┌─────────────────────────┐    WebSocket     ┌──────────────────────────────┐
│     React Frontend       │◄───────────────►│       FastAPI Backend         │
│  TanStack Query + Zustand│    REST API      │     LangGraph Pipeline       │
│  shadcn/ui + Tailwind    │                  │                              │
└─────────────────────────┘                  └──────────┬───────────────────┘
                                                        │
                    ┌───────────────────────────────────┼──────────────┐
                    │                                   │              │
           ┌────────▼────────┐                ┌────────▼────────┐     │
           │  LangGraph v3   │                │   Evaluation    │     │
           │  Agent Pipeline │                │  ATS + LLM Judge│     │
           │                 │                └─────────────────┘     │
           │  JD Analyzer    │                                        │
           │  Relevance Match│                ┌───────────────────┐   │
           │  Resume Writer  │                │   RAG Pipeline    │   │
           │  Quality Gate   │◄──────────────►│  ChromaDB + httpx │   │
           │  Cover Letter   │                │  Company Research │   │
           └────────┬────────┘                └───────────────────┘   │
                    │                                                  │
       ┌────────────┼────────────┐                                    │
       │            │            │                                    │
  ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌──────────┐ ┌───────┐  ┌────────▼────────┐
  │ Gemini  │ │ Claude  │ │ OpenAI  │ │ DeepSeek │ │ Qwen  │  │ LaTeX Compiler  │
  │   API   │ │   API   │ │ Compat  │ │   API    │ │  API  │  │ PDF Generation  │
  └─────────┘ └─────────┘ └─────────┘ └──────────┘ └───────┘  └─────────────────┘
                                                                     │
                                                            ┌────────▼────────┐
                                                            │   PostgreSQL    │
                                                            │   (optional)    │
                                                            └─────────────────┘
```

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **LaTeX** (MiKTeX on Windows, TeX Live on Linux/Mac)
- **spaCy English model** — required for ATS skill matching (`python -m spacy download en_core_web_sm`)
- At least one API key: [Google AI Studio](https://aistudio.google.com/), [Anthropic](https://console.anthropic.com/), [DeepSeek](https://platform.deepseek.com/), [Alibaba DashScope (Qwen)](https://dashscope.console.aliyun.com/), or a local proxy
- The `sentence-transformers` model (~90 MB) auto-downloads on first ATS evaluation — no manual step needed

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and configure
cp backend/.env.example backend/.env
# Edit backend/.env with your API key(s)

# Start all services
docker-compose up --build
```

The app opens at **http://localhost:3000** (frontend) with the API at **http://localhost:48765**.

### Option 2: Windows Installer

1. Run `install.bat`
2. Edit `backend/.env` with your API key
3. Run `start.bat`

The app opens at **http://localhost:45173**.

### Option 3: Manual Installation

#### System Dependencies

**Windows:** Install [MiKTeX](https://miktex.org/) — set "Install missing packages on-the-fly" to **Always**.

**Ubuntu/Debian:**
```bash
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**macOS:**
```bash
brew install --cask mactex
```

#### Backend

```bash
cd backend

# Option A: uv (recommended)
pip install uv
uv sync

# Option B: pip
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API key(s)

# Download spaCy model (required for ATS scoring)
python -m spacy download en_core_web_sm
```

#### Frontend

```bash
cd frontend
npm install
```

#### Running

**Backend** (terminal 1):
```bash
cd backend && python main.py
```

**Frontend** (terminal 2):
```bash
cd frontend && npm run dev
```

Open **http://localhost:45173**.

## Manual Setup Requirements

Some features require one-time manual setup beyond installing dependencies:

| Requirement | Why | How |
|---|---|---|
| **API Key(s)** | At least one AI provider needed | Settings panel or `backend/.env` |
| **LaTeX (pdflatex)** | PDF generation | MiKTeX (Windows) / TeX Live (Linux/Mac) |
| **spaCy model** | ATS skill matching | `python -m spacy download en_core_web_sm` |
| **User Information** | Your resume data for AI to use | Edit via Prompts panel in UI |
| **Chinese fonts** (optional) | Chinese PDF generation | Install Noto Sans CJK or similar CJK font |
| **ChromaDB** (optional) | Company research RAG | `pip install chromadb` (auto-installed with `uv sync`) |

**Auto-handled** (no manual action):
- `sentence-transformers` model (~90 MB, auto-downloads on first ATS evaluation)
- Python dependencies (via `uv sync` or `pip install`)
- Node.js dependencies (via `npm install`)
- Settings persistence (`backend/settings.json` auto-created on first run)

## Usage

1. **Create a Task** — click "New Task" in the sidebar (`Ctrl+N`)
2. **Paste Job Description** — paste the full JD into the text area
3. **Choose Options** — select template, language, provider, pipeline version (v3/v2), and toggle cover letter
4. **Research Company** (optional) — enter the company URL and click "Research" to index company info for RAG
5. **Add Application Questions** (optional) — type questions and set word limits
6. **Start** — click "Start Task" (`Ctrl+Enter`)
7. **Monitor** — watch the multi-agent pipeline progress in real-time
8. **Evaluate** — view ATS score breakdown, matched/missing keywords, and expert review
9. **Download** — grab the PDF, preview inline, or download LaTeX source
10. **Copy Answers** — use the Generated Answers panel to copy individual or all answers

## Configuration

All settings are configurable from the **Settings** panel in the UI and persisted to `backend/settings.json`.

### AI Providers

| Provider | Config Keys | Notes |
|----------|-------------|-------|
| Google Gemini | `gemini_api_key`, `gemini_model` | Supports thinking levels, Google Search grounding |
| Anthropic Claude | `claude_api_key`, `claude_model` | Direct Anthropic API |
| Claude Code Proxy | `claude_proxy_base_url`, `claude_proxy_model` | Uses SSE streaming to avoid response truncation |
| OpenAI-Compatible | `openai_compat_api_key`, `openai_compat_base_url`, `openai_compat_model` | Works with any OpenAI-compatible endpoint |
| DeepSeek | `deepseek_api_key`, `deepseek_model` | DeepSeek Chat, DeepSeek Reasoner |
| Qwen (DashScope) | `qwen_api_key`, `qwen_model` | Qwen Plus, Max, Turbo via Alibaba Cloud |

### Generation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Temperature | `1.0` | Creativity (0.0–2.0) |
| Max Output Tokens | Model default | Maximum response length |
| Thinking Level | `high` | Gemini 3+ reasoning depth: `low`, `high` |
| Google Search | `false` | Web search grounding for company research |
| Max LaTeX Retries | `3` | Auto-retry LaTeX compilation on errors |

### Server Ports

Default ports are chosen to avoid common conflicts (`8000`, `5173`):

| Setting | Default | Description |
|---------|---------|-------------|
| `PORT` | `48765` | Backend API server port |
| `FRONTEND_PORT` | `45173` | Frontend dev server port (also used for CORS) |

Override in `backend/.env`:
```env
PORT=9999
FRONTEND_PORT=9998
```

For the frontend Vite proxy, set `VITE_BACKEND_PORT` if backend uses a custom port:
```bash
VITE_BACKEND_PORT=9999 npm run dev
```

### Prompt Templates

Edit via the **Prompts** panel in the UI or directly in `backend/prompts/`:

| File | Description |
|------|-------------|
| `User_information_prompts.txt` | Your personal info (education, experience, skills) |
| `Resume_format_prompts.txt` | LaTeX template structure |
| `Resume_prompts.txt` | Main resume generation prompt |
| `Cover_letter_prompt.txt` | Cover letter generation prompt |
| `Application_question_prompt.txt` | Application question answering prompt |
| `User_information_prompts_zh.txt` | Your personal info (Chinese version) |
| `Resume_prompts_zh.txt` | Resume generation prompt (Chinese) |
| `Resume_format_prompts_zh.txt` | LaTeX template structure (Chinese) |
| `Cover_letter_prompt_zh.txt` | Cover letter prompt (Chinese) |
| `Application_question_prompt_zh.txt` | Application question prompt (Chinese) |

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
| `POST` | `/api/tasks/{id}/start` | Start processing (v2 pipeline) |
| `POST` | `/api/tasks/{id}/start-v3` | Start processing (v3 multi-agent pipeline) |
| `POST` | `/api/tasks/{id}/retry` | Retry a failed/completed task |
| `POST` | `/api/tasks/{id}/cancel` | Cancel a running task |
| `DELETE` | `/api/tasks/{id}` | Delete a task |
| `DELETE` | `/api/tasks` | Clear completed tasks |
| `GET` | `/api/tasks/{id}/resume` | Download resume PDF |
| `GET` | `/api/tasks/{id}/cover-letter` | Download cover letter PDF |
| `GET` | `/api/tasks/{id}/latex` | Download LaTeX source |
| `GET` | `/api/tasks/{id}/cover-letter-text` | Get cover letter plain text (for copy-paste) |

### Evaluation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks/{id}/evaluation` | Get ATS score breakdown (fast, no LLM) |
| `POST` | `/api/tasks/{id}/evaluate` | Full evaluation (ATS + LLM judge) |

### Company Research (RAG)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/companies/scrape` | Scrape and index a company website |
| `GET` | `/api/companies/{name}/info` | Get indexed company data |
| `DELETE` | `/api/companies/{name}` | Clear company cache |
| `GET` | `/api/companies` | List indexed companies |

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
├── agents/                    # LangGraph multi-agent pipeline (v3)
│   ├── graph.py               # StateGraph definition with conditional routing
│   ├── state.py               # ResumeState TypedDict
│   ├── schemas.py             # Pydantic structured output schemas
│   ├── jd_analyzer.py         # Job description analysis agent
│   ├── relevance_matcher.py   # Profile-to-JD matching agent
│   ├── resume_writer.py       # LaTeX resume generation agent
│   ├── quality_gate.py        # ATS scoring + retry routing
│   ├── cover_letter_writer.py # Cover letter generation agent
│   └── finalize.py            # LaTeX compilation + PDF output
├── evaluation/                # Automated resume evaluation
│   ├── ats_scorer.py          # Hybrid 6-method ATS scoring (BM25, semantic, skills, fuzzy, quality, section-aware)
│   ├── skills_taxonomy.py     # 550+ curated tech skills + synonym normalization
│   ├── llm_judge.py           # LLM-as-a-judge (5-rubric evaluation)
│   ├── feedback_generator.py  # Score-to-feedback conversion
│   └── metrics.py             # Combined evaluation pipeline
├── rag/                       # Company research (RAG pipeline)
│   ├── scraper.py             # Web scraping (httpx + BeautifulSoup)
│   ├── chunker.py             # Text chunking with metadata
│   ├── embeddings.py          # Embedding model wrapper
│   ├── vector_store.py        # ChromaDB vector store
│   ├── retriever.py           # Corrective RAG retrieval
│   └── tools.py               # LangGraph tool nodes
├── db/                        # Database layer (optional PostgreSQL)
│   ├── base.py                # SQLAlchemy DeclarativeBase
│   ├── models.py              # ORM models (Profile, Task, Version, Metadata)
│   └── session.py             # Async session factory
├── api/
│   ├── routes.py              # REST API endpoints
│   └── websocket.py           # WebSocket connection manager
├── services/
│   ├── task_manager.py        # Task orchestration and persistence
│   ├── langgraph_executor.py  # v3 pipeline executor
│   ├── provider_registry.py   # AI provider factory
│   ├── ai_client_base.py      # Abstract base class for AI providers
│   ├── gemini_client.py       # Google Gemini provider
│   ├── claude_client.py       # Anthropic Claude provider
│   ├── claude_proxy_client.py # Claude via local proxy (SSE streaming)
│   ├── openai_compat_client.py# OpenAI-compatible provider
│   ├── deepseek_client.py    # DeepSeek provider
│   ├── qwen_client.py        # Qwen (DashScope) provider
│   ├── prompt_manager.py      # Prompt loading and substitution
│   ├── settings_manager.py    # Settings persistence
│   ├── latex_compiler.py      # LaTeX to PDF compilation
│   ├── latex_utils.py         # LaTeX response parsing and cleanup
│   ├── pdf_extractor.py       # PDF text extraction (fitz/PyMuPDF)
│   ├── pdf_page_counter.py    # PDF page count validation
│   └── text_to_pdf.py         # Plain-text to PDF fallback (ReportLab)
├── middleware/
│   └── rate_limit.py          # slowapi rate limiting
├── alembic/                   # Database migrations
├── prompts/                   # Prompt template files
├── templates/                 # Resume style templates
├── tests/
│   ├── unit/
│   │   ├── agents/            # Agent unit tests (jd_analyzer, relevance_matcher, resume_writer, cover_letter_writer, finalize)
│   │   ├── test_ai_clients.py
│   │   ├── test_evaluation.py
│   │   ├── test_latex_compiler.py
│   │   ├── test_latex_utils.py
│   │   ├── test_pdf_extractor.py
│   │   ├── test_pdf_page_counter.py
│   │   ├── test_provider_registry.py
│   │   ├── test_rag.py
│   │   ├── test_routes.py
│   │   ├── test_settings_manager.py
│   │   ├── test_task_manager.py
│   │   ├── test_websocket_manager.py
│   │   └── test_chinese_pipeline.py  # Chinese language pipeline tests
│   ├── integration/           # Graph flow, LangGraph executor, mocked pipeline, state machine tests
│   └── e2e/                   # Full API lifecycle tests
│       └── test_zh_examples_report.py # Chinese E2E tests
├── config.py                  # Pydantic settings
├── main.py                    # FastAPI app with lifespan
├── pyproject.toml             # Project config (uv/pip)
├── Dockerfile                 # Multi-stage Docker build
└── requirements.txt           # Legacy pip dependencies

frontend/
├── src/
│   ├── components/
│   │   ├── ui/                # shadcn-style components (Button, Card, Badge, Progress)
│   │   ├── TaskPanel.tsx      # Main task UI + pipeline selector + company research
│   │   ├── TaskSidebar.tsx    # Task list sidebar
│   │   ├── QuestionsSection.tsx # Application questions CRUD
│   │   ├── SettingsPanel.tsx  # Settings modal (all providers)
│   │   ├── PromptsPanel.tsx   # Prompt template editor
│   │   ├── ProgressDisplay.tsx# Real-time step progress
│   │   ├── AgentProgress.tsx  # v3 pipeline visualization
│   │   ├── SkillMatchChart.tsx# ATS score breakdown visualization
│   │   └── ToastContainer.tsx # Toast notifications
│   ├── hooks/
│   │   ├── useTaskQuery.ts    # TanStack Query hooks (queries + mutations)
│   │   └── useWebSocket.ts    # WebSocket connection hook
│   ├── schemas/task.ts        # Zod validation schemas
│   ├── store/taskStore.ts     # Zustand (UI state only)
│   ├── lib/utils.ts           # cn() utility (clsx + tailwind-merge)
│   ├── types/task.ts          # TypeScript type definitions
│   └── tests/                 # Vitest + Testing Library tests
│       ├── App.test.tsx
│       ├── taskStore.test.ts
│       ├── useWebSocket.test.ts
│       ├── TaskSidebar.test.tsx
│       ├── TaskPanel.test.tsx
│       ├── SettingsPanel.test.tsx
│       ├── ProgressDisplay.test.tsx
│       ├── QuestionsSection.test.tsx
│       ├── schemas.test.ts
│       └── utils.test.ts
├── Dockerfile                 # Multi-stage Docker build (Vite → nginx)
├── nginx.conf                 # nginx config with API proxy
├── vitest.config.ts           # Test runner config
├── package.json
└── vite.config.ts

docker-compose.yml             # Backend + Frontend + PostgreSQL
.github/workflows/
├── ci.yml                     # Lint + test (backend & frontend)
└── security.yml               # Bandit + dependency audit
commitlint.config.js           # Conventional commit enforcement
```

## Development

### Running Tests

**Backend** (350+ tests):
```bash
cd backend

# With uv
uv run pytest --cov --cov-report=term-missing

# With pip
pytest --cov --cov-report=term-missing

# Run specific test categories
pytest tests/unit/                         # Unit tests only
pytest tests/integration/                  # Integration tests only
pytest tests/unit/agents/                  # Agent tests only
pytest tests/unit/test_latex_compiler.py   # Single file
```

**Frontend** (110+ tests):
```bash
cd frontend
npm test              # Single run
npm run test:watch    # Watch mode
```

### Linting

**Backend:**
```bash
cd backend
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy .              # Type check
```

**Frontend:**
```bash
cd frontend
npx tsc --noEmit           # Type check
```

### Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(agents): add quality gate retry routing
fix(latex): handle empty href commands
test(evaluation): add ATS scorer tests
docs(readme): update architecture diagram
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `pdflatex not found` | Install MiKTeX (Windows) or texlive (Linux/Mac) |
| `pdflatex timed out` | Open MiKTeX Console, set "Install missing packages" to "Always" |
| WebSocket connection failed | Ensure backend is running on port 48765 |
| `Errno 10048: port already in use` | Kill the existing process: `netstat -ano \| findstr :48765`, then `taskkill /PID <pid> /F` |
| Proxy response truncation | The Claude Code Proxy client uses SSE streaming by default |
| `Thinking level not supported` | Use a Gemini 3+ model (e.g., `gemini-3.1-pro-preview`) |
| ChromaDB import error | Install with `pip install chromadb` (optional — RAG features disabled without it) |
| Chinese PDF shows boxes | Install a CJK font (e.g., Noto Sans CJK) and restart the backend |
| `spacy model not found` | Run `python -m spacy download en_core_web_sm` |
| DeepSeek/Qwen API errors | Verify API key in Settings panel, check provider rate limits |
| Docker build fails on LaTeX | Ensure texlive packages are available in the Docker build context |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | LangGraph (StateGraph with conditional edges) |
| LLM Providers | Gemini, Claude, OpenAI-compatible, DeepSeek, Qwen |
| Evaluation | Hybrid ATS scorer (BM25, spaCy, sentence-transformers, rapidfuzz) + LLM-as-a-Judge |
| RAG | ChromaDB + httpx/BeautifulSoup + sentence-transformers |
| Backend | FastAPI + SQLAlchemy 2.0 async + Pydantic v2 |
| Frontend | React 18 + TypeScript + Vite |
| UI Components | shadcn/ui pattern (cva + tailwind-merge) |
| Server State | TanStack Query v5 |
| Client State | Zustand |
| Validation | Zod (frontend) + Pydantic (backend) |
| Styling | Tailwind CSS with dark mode |
| PDF | LaTeX compilation (pdflatex) + ReportLab |
| Testing | pytest + Vitest + Testing Library |
| CI/CD | GitHub Actions (ruff, mypy, pytest, tsc, vitest) |
| Containers | Docker multi-stage + docker-compose |
| Security | Bandit scan, slowapi rate limiting, dependency audit |

## License

MIT License
