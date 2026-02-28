# Implementation Notes: v2.3.0 → v3.0.0 Upgrade

This document maps every improvement proposed in `Improvement.md` to the concrete implementation decisions, files created, and trade-offs made during the v3.0 upgrade.

---

## Phase 0: Foundation & Tooling

### Python Tooling Migration

**Proposal:** Migrate from `requirements.txt` to `pyproject.toml` with `uv`, add `ruff` + `mypy`.

**Implementation:**

| File | Purpose |
|------|---------|
| `backend/pyproject.toml` | Central project config replacing `requirements.txt`. All phase dependencies declared upfront (LangGraph, SQLAlchemy, spaCy, ChromaDB, etc.). Dev dependencies include pytest-asyncio, pytest-cov, ruff, mypy, bandit. pytest configured with `asyncio_mode = "auto"` and `--cov-fail-under=60`. |
| `backend/ruff.toml` | Targets Python 3.11, line-length 120. Selects E/W/F/I/N/UP/B/A/C4/SIM/TCH/RUF rules. Ignores B008 (FastAPI `Depends()`) and A003 (shadowing builtins in Pydantic models). |
| `backend/mypy.ini` | `ignore_missing_imports = true` (gradual adoption), `check_untyped_defs = true`. |

**Trade-off:** Kept `requirements.txt` alongside `pyproject.toml` for backward compatibility — existing users can still `pip install -r requirements.txt` while new development uses `uv sync`.

### Database Layer (PostgreSQL + SQLAlchemy 2.0 async)

**Proposal:** SQLAlchemy 2.0 async with asyncpg, Alembic migrations, dual persistence.

**Implementation:**

| File | Purpose |
|------|---------|
| `backend/db/base.py` | `DeclarativeBase` + `TimestampMixin` (auto `created_at`/`updated_at`) |
| `backend/db/models.py` | Four ORM models: `Profile`, `GenerationTask`, `ResumeVersion`, `LLMGenerationMetadata`. Uses PostgreSQL JSONB for evaluation scores, UUID primary keys. `ResumeVersion` has `parent_version_id` for version tree tracking. |
| `backend/db/session.py` | Lazy engine/session factory. `get_db_session()` async context manager with commit/rollback. **Gracefully skips if `DATABASE_URL` not configured** — this enables the dual persistence strategy. |
| `backend/alembic/env.py` | Async Alembic configuration using `async_engine_from_config`. |
| `backend/alembic/script.py.mako` | Migration template. |

**Design decision:** The DB layer is entirely optional. If `DATABASE_URL` is empty (the default), the app continues using JSON file persistence exactly as before. This means existing users upgrading to v3 don't need PostgreSQL until they want it.

**Modified:** `backend/config.py` — added `database_url` and `database_echo` fields. `backend/main.py` — calls `await init_db()` on startup, `await close_db()` on shutdown.

### CI/CD Pipeline

**Proposal:** GitHub Actions with path filters.

**Implementation:**

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Four parallel jobs: `backend-lint` (ruff check, ruff format, mypy), `backend-test` (pytest --cov), `frontend-lint` (tsc --noEmit), `frontend-test` (vitest). Uses `astral-sh/setup-uv` for Python, `setup-node@v4` for frontend. |
| `.github/workflows/security.yml` | Bandit security scan + dependency audit (safety for Python, npm audit for frontend). Runs weekly + on push to `backend/**`. |

### Testing Infrastructure

**Implementation:**

| File | Purpose |
|------|---------|
| `backend/tests/unit/test_task_manager.py` | Comprehensive tests: create/get/delete/retry/cancel tasks, persistence, JD history, templates, filename sanitization. |
| `backend/tests/unit/test_routes.py` | API route tests using httpx `AsyncClient`. |
| `backend/tests/conftest.py` | Shared fixtures: temp prompt dirs, isolated task manager, mock settings. |

---

## Phase 1: LangGraph Multi-Agent Pipeline

**Proposal:** Replace single AI call with multi-agent StateGraph. Quality-gated retries. Keep v2 as fallback.

### Core Architecture

The pipeline follows this flow:
```
JD Analyzer → Relevance Matcher → [Company Research?] → Resume Writer → Quality Gate
    → (retry if score < 0.7, max 2) → Compile LaTeX → [Extract Text → Cover Letter
    → Cover Letter PDF] → Finalize
```

**Implementation:**

| File | Purpose |
|------|---------|
| `backend/agents/state.py` | `ResumeState(TypedDict)` — the shared state flowing through all nodes. Input fields, agent output fields (jd_analysis, relevance_match, latex_source, quality_score), metadata (agent_outputs for per-node latency/token tracking), and `company_context` (Phase 4 RAG). |
| `backend/agents/schemas.py` | Pydantic schemas for structured outputs: `JDAnalysis` (job_title, required_skills, preferred_skills, experience_level, key_responsibilities, industry), `RelevanceMatch` (matched_skills, missing_skills, emphasis_points, match_score), `QualityEvaluation`. |
| `backend/agents/graph.py` | `StateGraph` definition. Entry: jd_analyzer. Conditional edges: quality_gate → resume_writer (retry) or compile_latex; compile_latex → extract_text (cover letter) or finalize; relevance_matcher → retrieve_company (if RAG data exists) or resume_writer. |
| `backend/agents/jd_analyzer.py` | Sends structured JSON extraction prompt. Handles markdown-wrapped JSON responses. Falls back to default `JDAnalysis` on parse failure. Tracks latency in `agent_outputs`. |
| `backend/agents/relevance_matcher.py` | Matches user profile against JD requirements. Returns matched/missing skills, emphasis points, and a 0-1 match score. |
| `backend/agents/resume_writer.py` | Uses existing `PromptManager` infrastructure + agent enhancement prefix. Prepends job-specific instructions (matched skills, emphasis points). Includes `quality_feedback` from retry attempts and `company_context` from RAG. |
| `backend/agents/quality_gate.py` | Heuristic scoring: structure (25%), keyword match (35%), length (15%), formatting (25%). Uses `evaluation.ats_scorer` when available, falls back to heuristic. `QUALITY_THRESHOLD = 0.7`, `MAX_RETRIES = 2`. |
| `backend/agents/cover_letter_writer.py` | Enhancement prefix with job title, company, emphasis points, industry, and company context from RAG. Uses existing `PromptManager` for base prompt. |
| `backend/agents/finalize.py` | Four nodes: `compile_latex_node` (LaTeX compilation with page-check retry), `extract_text_node` (PDF text extraction), `create_cover_letter_pdf_node`, `finalize_node` (copy to final location). |
| `backend/services/langgraph_executor.py` | `run_langgraph_pipeline(task, progress_callback)` — main executor. Maps LangGraph node names to v2 `TaskStep` values for WebSocket broadcasting. Streams updates via `graph.astream(stream_mode="updates")`, then invokes `graph.ainvoke()` for final state. |

**Design decisions:**
1. **v2 fallback:** Added `POST /api/tasks/{task_id}/start-v3` endpoint alongside existing `/start`. Frontend has a toggle to choose pipeline version. The `Task` model gained a `pipeline_version` field.
2. **Existing infrastructure reuse:** Resume writer and cover letter writer use the existing `PromptManager` and provider system rather than creating separate LangChain LLM wrappers. This avoids duplicating provider configuration.
3. **Progress mapping:** LangGraph node events are mapped to existing `TaskStep` enum values so the WebSocket broadcasting and frontend `ProgressDisplay` work without major changes.

**Modified files:**
- `backend/api/routes.py` — v3 start endpoint
- `backend/services/task_manager.py` — `run_task_v3()` method
- `backend/models/task.py` — `pipeline_version` field
- `frontend/src/components/TaskPanel.tsx` — pipeline version selector
- `frontend/src/components/ProgressDisplay.tsx` — v3 node label mapping
- `frontend/src/types/task.ts` — `pipeline_version` and `node` fields

**Tests:**
- `backend/tests/unit/agents/test_quality_gate.py` — heuristic scoring, retry routing
- `backend/tests/unit/agents/test_jd_analyzer.py` — JSON parsing, fallback behavior
- `backend/tests/integration/test_graph_flow.py` — graph structure, conditional routing, agent output tracking

---

## Phase 2: Automated Evaluation & Self-Critique

**Proposal:** Deterministic ATS scoring + LLM-as-a-judge. Combined score drives quality gate retry. Self-critique feedback loop.

### Evaluation Pipeline

**Implementation:**

| File | Purpose |
|------|---------|
| `backend/evaluation/ats_scorer.py` | `ATSScoreBreakdown` dataclass with 6 sub-scores. `score_resume()` weighted scoring: 40% keyword match, 20% experience alignment, 10% format, 10% action verbs, 10% readability, 10% section completeness. Extracts plain text from LaTeX, identifies 40+ action verbs, checks expected sections. Returns matched/missing keywords. |
| `backend/evaluation/llm_judge.py` | `LLMJudgeResult` dataclass with 5-rubric scores (keyword_alignment, professional_tone, quantified_achievements, relevance, ats_compliance) + reasoning + improvement suggestions. Sends structured rubric prompt, parses JSON response. |
| `backend/evaluation/feedback_generator.py` | `generate_feedback()` converts scores into actionable feedback strings. `compute_combined_score()` weighted average (default 0.6 ATS + 0.4 LLM). |
| `backend/evaluation/metrics.py` | `evaluate_resume()` orchestrator: runs ATS scoring + optional LLM judge. Returns comprehensive dict with all scores, breakdowns, keywords, feedback, and pass/fail flag. |

**API endpoints:**
- `GET /api/tasks/{id}/evaluation` — fast ATS-only scoring (no LLM call)
- `POST /api/tasks/{id}/evaluate` — full evaluation with LLM judge

**Integration with quality gate:** The quality gate node in the LangGraph pipeline calls `ats_scorer.score_resume()` with fallback to heuristic scoring. If the score is below 0.7 and retries < 2, the graph routes back to `resume_writer` with the feedback appended to the prompt.

**Design decision:** Used simple keyword extraction and action verb detection rather than requiring spaCy as a hard dependency. spaCy adds ~500MB to the install; the simpler approach works well enough for the quality gate use case and keeps the project lighter.

**Tests:** `backend/tests/unit/test_evaluation.py` — good vs. minimal resume scoring, action verb detection, combined score computation, feedback generation.

---

## Phase 3: Frontend Modernization

**Proposal:** shadcn/ui, TanStack Query, react-hook-form + Zod, visualizations.

### Component Library (shadcn/ui pattern)

**Implementation:**

| File | Purpose |
|------|---------|
| `frontend/src/lib/utils.ts` | `cn()` utility combining `clsx` + `tailwind-merge` for conditional class merging. |
| `frontend/src/components/ui/button.tsx` | shadcn-style Button with `class-variance-authority`. Variants: default, destructive, outline, secondary, ghost, success. Sizes: default, sm, lg, icon. |
| `frontend/src/components/ui/card.tsx` | Card, CardHeader, CardTitle, CardContent with dark mode support. |
| `frontend/src/components/ui/badge.tsx` | Badge variants: default, success, warning, error, secondary, purple. |
| `frontend/src/components/ui/progress.tsx` | Animated progress bar. |

**Design decision:** Created components from scratch following shadcn patterns rather than running `npx shadcn@latest init`, which would have added Radix UI as a heavy dependency. The project only needs basic components, not the full Radix suite.

### Server State (TanStack Query v5)

| File | Purpose |
|------|---------|
| `frontend/src/hooks/useTaskQuery.ts` | 7 query hooks: `useTasksQuery` (5s refetch), `useTaskQuery` (3s refetch), `useTemplatesQuery` (stale: Infinity), `useSettingsQuery`, `usePromptsQuery`, `useEvaluationQuery`. 7 mutation hooks: create, start (v2/v3 aware), update settings, retry, cancel, delete, evaluate. All mutations invalidate relevant query caches. |
| `frontend/src/App.tsx` | Wrapped with `QueryClientProvider`. Default staleTime: 10s, retry: 1, refetchOnWindowFocus: false. |

**Design decision:** Kept Zustand for UI-only state (darkMode, activeTaskId, toasts) alongside TanStack Query for server state. The existing `useWebSocket` hook continues to update Zustand store for real-time progress — TanStack Query handles initial data loading and mutations.

### Form Validation (Zod)

| File | Purpose |
|------|---------|
| `frontend/src/schemas/task.ts` | `taskCreateSchema` (with language enum validation), `taskSettingsSchema`, `questionSchema` (word_limit 50-1000), `settingsSchema` (temperature 0-2, URL validation). |

### Visualizations

| File | Purpose |
|------|---------|
| `frontend/src/components/SkillMatchChart.tsx` | ATS score visualization with horizontal score bars (color-coded: green ≥70%, yellow ≥50%, red <50%), matched/missing keyword badges, and LLM judge results with improvement suggestions. |
| `frontend/src/components/AgentProgress.tsx` | v3 pipeline visualization: 6 nodes (JD Analysis, Profile Match, Resume Gen, Quality Check, PDF Compile, Cover Letter) with icons, animated status indicators, and connecting lines. Only renders for `pipeline_version === "v3"`. |

### Build & Test Config

| File | Purpose |
|------|---------|
| `frontend/tailwind.config.js` | Added `tailwindcss-animate` plugin, accordion keyframes. |
| `frontend/vitest.config.ts` | Vitest with jsdom, `@` path alias, globals: true. |
| `frontend/src/tests/setup.ts` | `@testing-library/jest-dom` import. |

**Modified:** `frontend/tsconfig.json` (path alias), `frontend/vite.config.ts` (path alias), `frontend/package.json` (new deps: @tanstack/react-query, cva, clsx, tailwind-merge, zod, react-hook-form, recharts, vitest).

---

## Phase 4: RAG Pipeline (Company Research)

**Proposal:** Scrape company info → chunk → embed → index in ChromaDB → retrieve during generation.

### RAG Module

| File | Purpose |
|------|---------|
| `backend/rag/scraper.py` | `scrape_company(url)` — httpx + BeautifulSoup4 scraper. Checks `robots.txt`, enforces 2s rate limiting per domain, tries common company paths (/about, /careers, /engineering, /blog). Max 5 pages per company. Extracts clean text by removing script/style/nav/footer elements. |
| `backend/rag/chunker.py` | `chunk_text()` — recursive character splitting (500 chars, 75 overlap). `prepare_chunks_with_metadata()` attaches source_url, company_name (lowercased), content_type, chunk_index, scraped_date. |
| `backend/rag/embeddings.py` | `embed_texts()` — tries sentence-transformers (BAAI/bge-small-en-v1.5) first, falls back to simple hash-based embeddings for dev/testing when sentence-transformers isn't installed. |
| `backend/rag/vector_store.py` | ChromaDB persistent client wrapper. `add_documents()`, `query()` (with optional company_name filter), `delete_company()`, `get_company_info()`, `list_companies()`. Cosine similarity space. Data persisted to `backend/data/chromadb/`. |
| `backend/rag/retriever.py` | **Corrective RAG pattern:** retrieve → grade relevance (distance ≤ 0.6) → if too few relevant results, rewrite query (strip stop words) → retrieve again. `scrape_and_index_company()` orchestrates the full scrape→chunk→embed→index flow. |
| `backend/rag/tools.py` | `retrieve_company_context_node()` — LangGraph node that retrieves company context. `should_retrieve_company()` — conditional edge function that checks if company data exists in vector store. |

**Design decisions:**
1. **httpx + BeautifulSoup** as primary scraper instead of Firecrawl — avoids requiring a paid API key for a core feature. Firecrawl could be added as an enhancement later.
2. **Graceful degradation:** If ChromaDB isn't installed, the RAG node is simply not added to the graph. The pipeline works identically to before. If company data doesn't exist in the vector store, the retrieval node is skipped via conditional edge.
3. **bge-small-en-v1.5** instead of BGE-M3 — smaller model (130MB vs 2.2GB), still good quality, faster to download and load.

### Graph Integration

The graph now has a conditional edge after `relevance_matcher`:
```
relevance_matcher → [has company data?]
    → YES: retrieve_company → resume_writer
    → NO: resume_writer (skip retrieval)
```

Company context is injected into both `resume_writer` and `cover_letter_writer` prompts when available.

### API Endpoints

- `POST /api/companies/scrape` — scrape + index a company website
- `GET /api/companies/{name}/info` — get indexed data
- `DELETE /api/companies/{name}` — clear company cache
- `GET /api/companies` — list all indexed companies

### Frontend

Added company URL input to `TaskPanel.tsx` with a "Research" button. Extracts company name from hostname. Shows scraping status (pages scraped, chunks indexed).

**Tests:** `backend/tests/unit/test_rag.py` — chunking, metadata attachment, embedding shape, relevance grading, query rewriting, HTML text extraction.

---

## Phase 5: Production Polish, Docker & Testing

### Docker Deployment

| File | Purpose |
|------|---------|
| `backend/Dockerfile` | Multi-stage: uv builder stage → slim production stage with texlive-latex-base, texlive-latex-extra, texlive-fonts-recommended. Health check via Python httpx call to `/health`. |
| `frontend/Dockerfile` | Multi-stage: Node 20 build stage → nginx:alpine serving. |
| `frontend/nginx.conf` | API proxy to `backend:8000`, WebSocket upgrade support, SPA fallback (`try_files $uri /index.html`), gzip compression, static asset caching (1 year). |
| `docker-compose.yml` | Three services: backend (FastAPI + texlive), frontend (nginx), postgres (16-alpine). Volumes for output, logs, data. Prompts and templates mounted from host for easy editing. |
| `.dockerignore` | Excludes .git, node_modules, venv, __pycache__, .env, logs, output, .claude. |

### Rate Limiting

| File | Purpose |
|------|---------|
| `backend/middleware/rate_limit.py` | slowapi integration. Default: 60/minute. Gracefully skips if slowapi not installed. |

**Modified:** `backend/main.py` — calls `setup_rate_limiting(app)` before CORS middleware.

### Git Hygiene

| File | Purpose |
|------|---------|
| `commitlint.config.js` | Conventional commit enforcement. Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert. Scopes: api, agents, evaluation, rag, latex, frontend, ui, docker, ci, config, db, tests. |

### Test Coverage

| File | Purpose |
|------|---------|
| `backend/tests/e2e/test_full_pipeline.py` | Full API lifecycle: health check, task CRUD, settings update, template listing, prompt validation, evaluation preconditions. |
| `backend/tests/integration/test_graph_flow.py` | Graph compilation, singleton behavior, quality gate routing (low score → retry, high score → continue, max retries → accept), cover letter routing (skip, generate, skip on error), company research routing, agent latency tracking. |
| `frontend/src/tests/App.test.tsx` | App renders, shows disconnected status, Settings/Prompts buttons present. |
| `frontend/src/tests/utils.test.ts` | `cn()` merging, conditional classes, Tailwind deduplication. |
| `frontend/src/tests/schemas.test.ts` | Zod schema validation: taskCreate (required JD, defaults, language enum), question (word limit range), settings (temperature bounds). |

---

## Files Summary

### New Files Created (~70 files)

**Backend — Agents (10):** `__init__.py`, `state.py`, `schemas.py`, `graph.py`, `jd_analyzer.py`, `relevance_matcher.py`, `resume_writer.py`, `quality_gate.py`, `cover_letter_writer.py`, `finalize.py`

**Backend — Evaluation (5):** `__init__.py`, `ats_scorer.py`, `llm_judge.py`, `feedback_generator.py`, `metrics.py`

**Backend — RAG (7):** `__init__.py`, `embeddings.py`, `chunker.py`, `scraper.py`, `vector_store.py`, `retriever.py`, `tools.py`

**Backend — Database (4):** `__init__.py`, `base.py`, `models.py`, `session.py`

**Backend — Middleware (2):** `__init__.py`, `rate_limit.py`

**Backend — Config (4):** `pyproject.toml`, `ruff.toml`, `mypy.ini`, `alembic.ini`

**Backend — Migrations (2):** `alembic/env.py`, `alembic/script.py.mako`

**Backend — Services (1):** `langgraph_executor.py`

**Backend — Tests (9):** `unit/test_task_manager.py`, `unit/test_routes.py`, `unit/test_evaluation.py`, `unit/test_rag.py`, `unit/agents/test_quality_gate.py`, `unit/agents/test_jd_analyzer.py`, `integration/test_graph_flow.py`, `e2e/test_full_pipeline.py`, + `__init__.py` files

**Frontend — UI Components (4):** `ui/button.tsx`, `ui/card.tsx`, `ui/badge.tsx`, `ui/progress.tsx`

**Frontend — New Components (2):** `SkillMatchChart.tsx`, `AgentProgress.tsx`

**Frontend — Hooks (1):** `useTaskQuery.ts`

**Frontend — Schemas (1):** `schemas/task.ts`

**Frontend — Lib (1):** `lib/utils.ts`

**Frontend — Tests (4):** `tests/setup.ts`, `tests/App.test.tsx`, `tests/utils.test.ts`, `tests/schemas.test.ts`

**Frontend — Config (2):** `vitest.config.ts`, `nginx.conf`

**Docker (3):** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`

**Root (4):** `.dockerignore`, `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `commitlint.config.js`

### Modified Files (~12 files)

- `backend/config.py` — database settings
- `backend/main.py` — v3.0.0 version, DB init, rate limiting
- `backend/models/task.py` — `pipeline_version` field
- `backend/api/routes.py` — v3 start endpoint, evaluation endpoints, company endpoints
- `backend/services/task_manager.py` — `run_task_v3()` method
- `frontend/src/App.tsx` — QueryClientProvider wrapper
- `frontend/src/components/TaskPanel.tsx` — pipeline selector, company URL input
- `frontend/src/components/ProgressDisplay.tsx` — v3 node labels
- `frontend/src/types/task.ts` — pipeline_version, node fields
- `frontend/package.json` — new dependencies, v3.0.0
- `frontend/tsconfig.json` — path aliases
- `frontend/vite.config.ts` — path aliases
- `frontend/tailwind.config.js` — tailwindcss-animate, accordion keyframes
- `.gitignore` — coverage, cassettes, chromadb patterns
