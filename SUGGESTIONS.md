# Resume Generator - Improvement Suggestions & Feature Extensions

This document contains a comprehensive analysis of the current codebase along with
prioritized suggestions for improvements, bug fixes, and new features.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Bug Fixes & Critical Issues](#1-bug-fixes--critical-issues)
3. [Code Quality & Architecture Improvements](#2-code-quality--architecture-improvements)
4. [UX / Frontend Enhancements](#3-ux--frontend-enhancements)
5. [New Feature Ideas](#4-new-feature-ideas)
6. [Performance & Scalability](#5-performance--scalability)
7. [DevOps & Deployment](#6-devops--deployment)
8. [Security Hardening](#7-security-hardening)
9. [Priority Roadmap](#priority-roadmap)

---

## Project Overview

The Resume & Cover Letter Generator is a full-stack application with:
- **Backend**: FastAPI (Python) with Gemini API integration, LaTeX compilation, PDF generation
- **Frontend**: React + TypeScript with Zustand state management, Tailwind CSS, WebSocket real-time updates
- **Workflow**: User pastes a job description -> Gemini generates a tailored LaTeX resume -> compiles to PDF -> optionally generates a cover letter -> validates page count -> outputs downloadable PDFs

---

## 1. Bug Fixes & Critical Issues

### 1.1 WebSocket Completion Check Misses Resume-Only Tasks
**File**: `frontend/src/hooks/useWebSocket.ts:58-64`

The WebSocket handler only fetches full task details when `create_cover_pdf` completes.
For resume-only tasks (cover letter disabled), the completion event is `compile_latex`, so
the frontend never fetches the final task details (including `resume_pdf_path`).

**Fix**: Check the task's `generate_cover_letter` flag or listen for both `compile_latex`
and `create_cover_pdf` completion events. Alternatively, have the backend send a dedicated
"task_completed" WebSocket message type.

### 1.2 In-Memory Task Storage Lost on Restart
**File**: `backend/services/task_manager.py:36`

All tasks are stored in a Python dictionary (`self.tasks: Dict[str, Task] = {}`). Any
server restart loses all task data and generated file references.

**Fix**: Add SQLite or JSON-file-based persistence. Even a simple JSON file written on
each task state change would prevent data loss.

### 1.3 Deprecated `asyncio.get_event_loop()` Usage
**Files**: `backend/services/task_manager.py:389`, `backend/services/gemini_client.py:291`

`asyncio.get_event_loop()` is deprecated in Python 3.10+ for getting the running loop.
Should use `asyncio.get_running_loop()` instead.

### 1.4 Deprecated FastAPI Lifecycle Events
**File**: `backend/main.py:44,57`

`@app.on_event("startup")` and `@app.on_event("shutdown")` are deprecated in newer
FastAPI versions. Should migrate to the `lifespan` context manager pattern.

### 1.5 Settings API Key Exposure
**File**: `backend/api/routes.py:50-53`

The `GET /api/settings` endpoint returns the full `gemini_api_key` to the frontend. This
is a security risk since the API key could be intercepted or logged by browser extensions.

**Fix**: Mask the API key in the response (e.g., return `"AIza...XXXX"` or an empty string)
and only accept it for writes.

### 1.6 Task Counter Resets on Restart
**File**: `backend/services/task_manager.py:96`

`self.task_counter` starts at 0 on each server start, so task numbers restart from 1. If
persistence is added, this could cause duplicate task numbers.

---

## 2. Code Quality & Architecture Improvements

### 2.1 Add a Testing Framework
There are **zero tests** in the project. Adding tests would greatly improve reliability:
- **Unit tests**: For `latex_utils.py` (extraction/post-processing), `prompt_manager.py`
  (template substitution), `pdf_page_counter.py`, `text_to_pdf.py`
- **Integration tests**: For the API routes with a test client
- **Recommended**: `pytest` + `pytest-asyncio` + `httpx` (for FastAPI test client)

### 2.2 Type Hints and Validation
- Several function signatures use `str = None` instead of `Optional[str] = None`
  (e.g., `task_manager.py:131`)
- Add `py.typed` marker and consider running `mypy` for static type checking

### 2.3 Error Handling Granularity
Currently, the entire `run_task` method is wrapped in a single try/except. Consider
more granular error handling per step so that partial results can be preserved (e.g., if
resume compiled successfully but cover letter generation fails, the resume PDF should
still be downloadable).

### 2.4 Separate Business Logic from I/O
The `TaskManager` class handles both orchestration and business logic. Consider extracting:
- A `ResumeService` for resume generation workflow
- A `CoverLetterService` for cover letter workflow
- Keep `TaskManager` as a thin orchestrator

### 2.5 Configuration Validation
Add startup validation that checks:
- LaTeX is installed (`pdflatex` is in PATH)
- Required prompt files exist and are non-empty
- API key is configured (warn if not)
- Output directories are writable

### 2.6 Consistent Logging
Some modules use `self.logger` while others use module-level `logger`. Standardize to
module-level loggers throughout.

### 2.7 Prompt Template Validation
When prompts are saved via the UI, validate that required placeholders
(`{{user_information}}`, `{{latex_template}}`, `{{JOB_DESCRIPTION}}`) are still present.
Warn the user if a placeholder is missing.

---

## 3. UX / Frontend Enhancements

### 3.1 Task Deletion
**Priority: High**

There is no way to delete tasks from the sidebar. Users will accumulate old/failed tasks
with no way to clean up.

**Implementation**:
- Add a `DELETE /api/tasks/{id}` endpoint
- Add a delete button (trash icon) on each sidebar task item
- Optionally add "Clear All Completed" bulk action

### 3.2 Task Retry / Re-run
**Priority: High**

Failed tasks cannot be retried. Users must create a new task and re-paste the job
description.

**Implementation**:
- Add a "Retry" button on failed tasks that resets the task to pending
- Or a "Clone Task" button that creates a new task with the same job description

### 3.3 In-Browser PDF Preview
**Priority: High**

Users must download the PDF to see the result. An in-browser preview would drastically
improve the feedback loop.

**Implementation**:
- Embed a PDF viewer using `<iframe>` or a library like `react-pdf`
- Show side-by-side: job description on the left, PDF preview on the right
- Add a "Refresh Preview" option after manual edits

### 3.4 Dark Mode
**Priority: Medium**

Add a dark mode toggle. Tailwind CSS makes this straightforward with the `dark:` variant.

### 3.5 Keyboard Shortcuts
**Priority: Medium**

- `Ctrl+Enter` to start a task
- `Ctrl+N` to create a new task
- `Ctrl+S` in the prompts editor to save
- `Escape` to close modals

### 3.6 Drag & Drop Job Description Input
**Priority: Low**

Allow users to drag and drop a `.txt` or `.pdf` file containing the job description
instead of copy-pasting.

### 3.7 Task Elapsed Time Display
**Priority: Low**

Show how long each step took and the total task duration. The backend already tracks
`started_at` and `completed_at` on steps - just display them.

### 3.8 Browser Notifications
**Priority: Low**

Send a browser notification when a task completes or fails, useful when the tab is in
the background.

### 3.9 Responsive / Mobile Layout
**Priority: Low**

The current layout uses a fixed `w-72` sidebar which doesn't work on mobile. Add a
collapsible sidebar or a bottom navigation for small screens.

### 3.10 Toast Notifications
**Priority: Low**

Replace the inline success/error messages in Settings and Prompts panels with toast
notifications that auto-dismiss, providing a cleaner UX.

---

## 4. New Feature Ideas

### 4.1 Multiple Resume Templates
**Priority: High**

Currently there is one hardcoded LaTeX template. Allow users to:
- Choose from a library of pre-built templates (e.g., "Modern", "Classic", "Minimal")
- Upload custom LaTeX templates
- Preview template styles before generating

**Implementation**:
- Create a `templates/` directory with multiple `.tex` files
- Add a template selector dropdown in the task panel
- Store template choice per task

### 4.2 Resume ATS Score / Keyword Match Analysis
**Priority: High**

After generation, analyze the resume against the job description:
- Calculate keyword match percentage
- Highlight missing critical keywords
- Suggest improvements
- Show an "ATS compatibility score"

**Implementation**:
- Add a post-generation analysis step using Gemini or simple keyword extraction (TF-IDF)
- Display a score card in the UI next to the download buttons

### 4.3 Multi-Version Generation & Comparison
**Priority: Medium**

Generate 2-3 different resume versions with different emphasis and let the user pick:
- Version A: Technical focus
- Version B: Leadership/impact focus
- Version C: Balanced

**Implementation**:
- Add a "Generate Multiple Versions" option
- Run multiple Gemini calls in parallel with different prompt variations
- Show a comparison view with tabs or side-by-side layout

### 4.4 Batch Processing / Bulk Generation
**Priority: Medium**

Allow users to paste multiple job descriptions (or upload a CSV) and generate
resumes for all of them in one go.

**Implementation**:
- Add a "Batch Mode" tab in the UI
- Accept multiple JDs separated by a delimiter or uploaded as a file
- Create tasks for each and process them with a configurable concurrency limit

### 4.5 Job Description History & Favorites
**Priority: Medium**

Save previously used job descriptions for quick reuse:
- Auto-save JDs when a task is started
- Allow starring/favoriting certain JDs
- Search through past JDs

### 4.6 Cover Letter Template Variety
**Priority: Medium**

The current cover letter is generated as plain text and converted to PDF with ReportLab.
Offer multiple styles:
- Professional/formal (current)
- Modern/creative
- LaTeX-formatted (matching resume template style)

### 4.7 Export to Multiple Formats
**Priority: Medium**

Currently only PDF output is supported. Add:
- DOCX export (using `python-docx`)
- Plain text / Markdown export
- LaTeX source download (already available internally)
- HTML export

### 4.8 Smart Company Research
**Priority: Medium**

Before generating, automatically research the company:
- Use Google Search grounding to fetch recent company news
- Extract company values, culture, recent projects
- Feed this context into the cover letter prompt

This partially exists via `gemini_enable_search` but could be more structured.

### 4.9 Resume Edit & Regenerate
**Priority: Medium**

After generation, allow users to:
- View and edit the raw LaTeX source in the browser
- Recompile without calling Gemini again
- Make manual tweaks and re-download

**Implementation**:
- Add a LaTeX editor panel (use a code editor like CodeMirror or Monaco)
- Add a "Recompile" button that sends the edited LaTeX to the backend
- Add a `POST /api/tasks/{id}/recompile` endpoint

### 4.10 Prompt Version History
**Priority: Low**

Track changes to prompts over time:
- Auto-save previous versions when a prompt is updated
- Allow rolling back to a previous prompt version
- Show a diff view between versions

### 4.11 LinkedIn Profile Import
**Priority: Low**

Allow importing user information from a LinkedIn profile:
- Accept a LinkedIn profile URL or PDF export
- Parse education, experience, skills
- Auto-populate the User Information prompt

### 4.12 Multi-Language Support
**Priority: Low**

Generate resumes in different languages:
- Add a language selector (English, French, Chinese, etc.)
- Modify prompts to instruct Gemini to generate in the target language
- Use appropriate LaTeX packages for non-Latin scripts

### 4.13 AI Model Selection
**Priority: Low**

Support multiple AI providers beyond Gemini:
- OpenAI GPT-4 / GPT-4o
- Anthropic Claude
- Local models via Ollama

This would require an adapter pattern for the AI client.

---

## 5. Performance & Scalability

### 5.1 Concurrent Task Limit
**Priority: Medium**

There is no limit on concurrent tasks. Multiple simultaneous Gemini API calls + LaTeX
compilations could overwhelm the system.

**Fix**: Add a semaphore or task queue (e.g., `asyncio.Semaphore`) to limit concurrent
processing (e.g., max 3 tasks at once).

### 5.2 LaTeX Compilation Caching
**Priority: Low**

If the same LaTeX code is compiled twice (e.g., during retries with no changes), cache
the result to avoid redundant compilation.

### 5.3 Frontend Bundle Optimization
**Priority: Low**

- Add code splitting for modal panels (Settings, Prompts) since they're not always shown
- Lazy load heavy components
- Consider Vite's `manualChunks` for vendor splitting

### 5.4 WebSocket Message Batching
**Priority: Low**

If many progress updates fire rapidly, batch them to reduce frontend re-renders.

---

## 6. DevOps & Deployment

### 6.1 Docker & Docker Compose
**Priority: High**

Add containerization for easy deployment:
- `Dockerfile` for the backend (Python + LaTeX)
- `Dockerfile` for the frontend (Node.js build + nginx)
- `docker-compose.yml` to orchestrate both services

### 6.2 CI/CD Pipeline
**Priority: Medium**

Add GitHub Actions or similar:
- Run linting (ESLint, Flake8/Ruff)
- Run tests (once added)
- Build check (frontend `tsc && vite build`)
- Optional: Auto-deploy to a staging server

### 6.3 Production Build Configuration
**Priority: Medium**

The commented-out static file serving in `main.py:87-90` suggests production deployment
isn't fully configured. Add:
- A production `docker-compose.prod.yml`
- Nginx reverse proxy configuration
- Environment-based configuration (dev/staging/prod)

### 6.4 Health Check Enhancement
**Priority: Low**

The `/health` endpoint is minimal. Add checks for:
- LaTeX installation status
- Gemini API connectivity
- Disk space for output directory
- Current task queue depth

---

## 7. Security Hardening

### 7.1 API Key Management
**Priority: High**

- Never return the full API key via the settings GET endpoint (mask it)
- Consider encrypting the API key at rest in `settings.json`
- Add a `.gitignore` entry for `settings.json` (currently only `.env` is ignored)

### 7.2 Rate Limiting
**Priority: Medium**

Add rate limiting to prevent abuse:
- Limit task creation (e.g., 10 tasks per minute)
- Limit Gemini API calls
- Use `slowapi` or a custom middleware

### 7.3 Input Sanitization
**Priority: Medium**

- Job descriptions are passed directly to prompts without sanitization
- Could contain prompt injection attempts targeting the Gemini API
- Add basic sanitization or length limits on input

### 7.4 File Path Traversal Prevention
**Priority: Medium**

The `download_resume` and `download_cover_letter` endpoints use paths stored on the task
object. Validate that the path is within the expected output directory.

### 7.5 Authentication & Authorization
**Priority: Low (for personal use) / High (for shared deployment)**

Currently there is no authentication. For shared deployments, add:
- Basic auth or API key-based auth
- Optional: OAuth/SSO integration

### 7.6 CORS Tightening
**Priority: Low**

The CORS configuration allows `localhost` origins with all methods and headers. For
production, restrict to the actual frontend origin.

---

## Priority Roadmap

### Phase 1 - Quick Wins (Immediate)
1. Fix WebSocket resume-only completion bug (1.1)
2. Add task deletion (3.1)
3. Add task retry/clone (3.2)
4. Mask API key in settings response (1.5)
5. Fix deprecated `asyncio.get_event_loop()` (1.3)

### Phase 2 - Core Experience (Short Term)
1. Add in-browser PDF preview (3.3)
2. Add task persistence (SQLite or JSON file) (1.2)
3. Add resume LaTeX editor + recompile (4.9)
4. Add multiple resume templates (4.1)
5. Add basic test suite (2.1)

### Phase 3 - Power Features (Medium Term)
1. ATS keyword score analysis (4.2)
2. Batch processing (4.4)
3. Job description history (4.5)
4. Export to DOCX/HTML (4.7)
5. Docker deployment (6.1)
6. Concurrent task limiting (5.1)

### Phase 4 - Polish & Scale (Long Term)
1. Multi-version generation & comparison (4.3)
2. Dark mode (3.4)
3. Multiple cover letter templates (4.6)
4. Multi-language support (4.12)
5. Multi-model AI support (4.13)
6. CI/CD pipeline (6.2)
7. Authentication system (7.5)

---

*Document generated on 2026-02-09 by analyzing the full project codebase.*
