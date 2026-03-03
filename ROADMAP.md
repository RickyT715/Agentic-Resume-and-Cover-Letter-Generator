# Resume Generator — Improvement Roadmap

> **Generated:** 2026-03-02 | **Baseline version:** v3.0.0 | **Target version:** v3.2.0

---

## Overview

This document catalogues **45 improvements** identified through a comprehensive codebase audit. Each item includes a unique ID, complexity estimate, affected files, concrete implementation steps, and verification criteria.

Items are organized into 9 phases ordered by risk and dependency: housekeeping first, then security, then correctness, and so on. Phases 0–3 can be parallelized. Phases 4–6 depend on Phase 3 (linting tooling). Phase 7 features are deferred to future sessions.

### Complexity Legend

| Label | Effort | Typical scope |
|-------|--------|---------------|
| **S** | < 30 min | Single file, config-only, or mechanical change |
| **M** | 30 min – 2 h | Cross-file, some logic, moderate testing |
| **L** | 2 – 6 h | Multi-component, new abstractions, thorough testing |
| **XL** | 6+ h | Architectural, phased rollout, integration testing |

### Status Key

- [ ] Not started
- [x] Completed

---

## Phase 0: Housekeeping & Quick Wins

> 7 items, all **S** complexity. Zero behavioral change — safe to batch-commit.

---

### P0-01: Remove `nul` Windows Artifacts

**Complexity:** S
**Files:** repository root (any `nul` files created by Windows path mishandling)

**Steps:**
1. Search for files literally named `nul` or `NUL` anywhere in the repo.
2. Delete them and add `nul` to `.gitignore`.
3. Commit the removal.

**Verification:**
- `git ls-files nul` returns empty.
- No `nul` file exists in working tree.

---

### P0-02: Add `.gitattributes`

**Complexity:** S
**Files:** `.gitattributes` (new)

**Steps:**
1. Create `.gitattributes` at repo root:
   ```
   # Auto-detect text files and normalize line endings
   * text=auto

   # Force LF for source code
   *.py text eol=lf
   *.ts text eol=lf
   *.tsx text eol=lf
   *.js text eol=lf
   *.json text eol=lf
   *.yaml text eol=lf
   *.yml text eol=lf
   *.md text eol=lf
   *.txt text eol=lf
   *.css text eol=lf
   *.html text eol=lf

   # Binary files
   *.pdf binary
   *.png binary
   *.ico binary
   *.woff2 binary
   ```

**Verification:**
- File exists, `git check-attr text -- "*.py"` returns `text: set`.

---

### P0-03: Remove Redundant `requirements.txt`

**Complexity:** S
**Files:** `backend/requirements.txt`

**Context:** The project uses `uv` + `pyproject.toml` for dependency management. `requirements.txt` is a stale subset (12 of 30+ packages) and misleads contributors.

**Steps:**
1. Delete `backend/requirements.txt`.
2. Update `backend/Dockerfile` if it references `requirements.txt` (currently it does not — uses `pyproject.toml`).
3. If any CI or docs reference it, update those too.

**Verification:**
- File is gone.
- `docker compose build` still succeeds.

---

### P0-04: Commit `uv.lock`

**Complexity:** S
**Files:** `.gitignore`, `backend/uv.lock`

**Context:** `.gitignore` has `backend/uv.lock` commented out, and the file exists on disk. Committing the lockfile ensures reproducible installs.

**Steps:**
1. Ensure the `.gitignore` line remains commented out (i.e., `uv.lock` is NOT ignored).
2. `git add backend/uv.lock` and commit.

**Verification:**
- `git ls-files backend/uv.lock` shows the file is tracked.

---

### P0-05: Sync Version Numbers to v3.2.0

**Complexity:** S
**Files:** `backend/pyproject.toml`, `frontend/package.json`

**Context:** Both currently read `"3.0.0"`. Bump to `3.2.0` to reflect the improvements in this roadmap.

**Steps:**
1. In `backend/pyproject.toml`: change `version = "3.0.0"` → `version = "3.2.0"`.
2. In `frontend/package.json`: change `"version": "3.0.0"` → `"version": "3.2.0"`.

**Verification:**
- `grep version backend/pyproject.toml` shows `3.2.0`.
- `node -e "console.log(require('./frontend/package.json').version)"` prints `3.2.0`.

---

### P0-06: Remove Dead Frontend Dependencies

**Complexity:** S
**Files:** `frontend/package.json`

**Context:** Three dependencies have zero imports in `frontend/src/`:
- `recharts ^2.0.0` — not used (SkillMatchChart uses plain CSS bars)
- `react-hook-form ^7.0.0` — not used
- `@hookform/resolvers ^3.3.0` — not used

**Steps:**
1. Run `npm uninstall recharts react-hook-form @hookform/resolvers` in `frontend/`.
2. Verify no import/require references remain.

**Verification:**
- `grep -r "recharts\|react-hook-form\|@hookform/resolvers" frontend/src/` returns nothing.
- `npm run build` succeeds.

---

### P0-07: Remove Unused `AgentProgress.tsx`

**Complexity:** S
**Files:** `frontend/src/components/AgentProgress.tsx`

**Context:** This component renders a v3 pipeline visualization but is not imported anywhere in the application. Verify before deleting.

**Steps:**
1. Search for `AgentProgress` across all `.ts`/`.tsx` files.
2. If no imports found, delete the file.
3. If imported somewhere, skip this item.

**Verification:**
- `grep -r "AgentProgress" frontend/src/` returns nothing (except the file itself, which should be deleted).
- `npm run build` succeeds.

---

## Phase 1: Security Hardening

> 7 items. Mix of **S**, **M**, and **L** complexity. Priority: protect against untrusted input.

---

### P1-01: Input Size Limits on Pydantic Models

**Complexity:** S
**Files:** `backend/models/task.py`

**Context:** `TaskCreate.job_description`, `ApplicationQuestion.question`, and other string fields have no `max_length` constraint. A client can send multi-MB payloads.

**Steps:**
1. Add `Field(max_length=50_000)` to `job_description` (generous for any JD).
2. Add `Field(max_length=1_000)` to `ApplicationQuestion.question`.
3. Add `Field(max_length=5_000)` to `ApplicationQuestion.answer`.
4. Add `Field(max_length=500)` to `company_name` (in `TaskCreate`).
5. Consider adding a validator that rejects null bytes in all string fields.

**Verification:**
- POST a 60 KB job description → 422 response.
- POST a normal-sized job description → 200 response.
- Existing tests still pass.

---

### P1-02: SSRF Protection for `/companies/scrape`

**Complexity:** M
**Files:** `backend/api/routes.py` (around line 82)

**Context:** `POST /api/companies/scrape` accepts an arbitrary URL and fetches it server-side with no validation. An attacker could probe internal networks (`http://169.254.169.254/`, `http://localhost:48765/`, etc.).

**Steps:**
1. Create a URL validator that:
   - Resolves the hostname to an IP address.
   - Rejects private/loopback/link-local IPs (RFC 1918, `127.0.0.0/8`, `169.254.0.0/16`, `::1`, `fc00::/7`).
   - Allows only `http` and `https` schemes.
   - Optionally maintains an allowlist of known job-board domains.
2. Apply the validator before making the HTTP request.
3. Return 400 with a clear message for rejected URLs.

**Verification:**
- `POST /api/companies/scrape` with `http://127.0.0.1` → 400.
- `POST /api/companies/scrape` with `http://169.254.169.254` → 400.
- `POST /api/companies/scrape` with a valid public URL → 200.

---

### P1-03: Apply Rate Limits to Routes

**Complexity:** M
**Files:** `backend/middleware/rate_limit.py`, `backend/api/routes.py`

**Context:** `rate_limit.py` defines `TASK_CREATE_RATE = "10/minute"` and `SCRAPE_RATE = "5/minute"` but never applies them. Only the global `60/minute` default is active.

**Steps:**
1. In `rate_limit.py`, export the per-route rate strings.
2. In `routes.py`, decorate sensitive endpoints with `@limiter.limit(...)`:
   - `POST /api/tasks` → `"10/minute"`
   - `POST /api/companies/scrape` → `"5/minute"`
   - `PUT /api/settings` → `"10/minute"`
3. Add appropriate error handling (429 responses with `Retry-After` header).
4. Make rate values configurable via environment variables.

**Verification:**
- Hit `POST /api/tasks` 11 times in 60 seconds → 429 on the 11th.
- Global rate limit still applies to other routes.

---

### P1-04: Add API Key Authentication

**Complexity:** L
**Files:** `backend/api/routes.py`, `backend/config.py`, `backend/middleware/` (new `auth.py`)

**Context:** All endpoints are completely open. Any network-adjacent client can create tasks, overwrite API keys via `PUT /api/settings`, and delete tasks.

**Steps:**
1. Add `api_auth_key: str = ""` to `config.py` Settings (empty = auth disabled, for backward compat).
2. Create `backend/middleware/auth.py` with a FastAPI dependency:
   - Check `X-API-Key` header or `api_key` query param against `settings.api_auth_key`.
   - If `api_auth_key` is empty, skip auth (development mode).
   - Return 401 for invalid keys.
3. Apply the dependency to the `APIRouter` or selectively to write endpoints.
4. Update frontend to send the key if configured (store in localStorage, add to fetch headers).
5. Document the env var in `.env.example`.

**Verification:**
- With `API_AUTH_KEY=secret` set: unauthenticated `POST /api/tasks` → 401.
- With `API_AUTH_KEY=secret` set: `POST /api/tasks` with `X-API-Key: secret` → 200.
- With `API_AUTH_KEY=` (empty): all requests pass without auth header.

---

### P1-05: Suppress Internal Error Details

**Complexity:** M
**Files:** `backend/api/routes.py`

**Context:** Unhandled exceptions may leak stack traces, file paths, and internal variable names to clients.

**Steps:**
1. Add a global exception handler in the FastAPI app that catches `Exception`:
   - Log the full traceback server-side at ERROR level.
   - Return a generic `{"detail": "Internal server error"}` with status 500.
2. For known exceptions (ValueError, FileNotFoundError, etc.), return appropriate 4xx codes with safe messages.
3. In development mode (`DEBUG=true`), optionally include the traceback for debugging.

**Verification:**
- Trigger an internal error → response body contains no stack trace.
- Server logs contain the full traceback.

---

### P1-06: Docker Non-Root User

**Complexity:** S
**Files:** `backend/Dockerfile`

**Context:** The Dockerfile runs everything as root. A container escape would give the attacker root on the host.

**Steps:**
1. In the production stage of the Dockerfile, add:
   ```dockerfile
   RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
   RUN chown -R appuser:appuser /app
   USER appuser
   ```
2. Place this before the `CMD` instruction.
3. Ensure the output directory (`/app/output/`) is writable by `appuser`.

**Verification:**
- `docker compose exec backend whoami` returns `appuser`.
- Task creation + PDF generation still works inside the container.

---

### P1-07: Externalize Docker Compose Credentials

**Complexity:** S
**Files:** `docker-compose.yml`

**Context:** Postgres credentials are hardcoded (`resumegen:resumegen`). Missing env var forwarding for some API keys.

**Steps:**
1. Replace hardcoded values with `${VARIABLE:-default}` syntax:
   ```yaml
   POSTGRES_USER: ${POSTGRES_USER:-resumegen}
   POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-resumegen}
   POSTGRES_DB: ${POSTGRES_DB:-resumegen}
   ```
2. Update the `DATABASE_URL` to use the same variables.
3. Forward missing API keys to the backend service:
   ```yaml
   OPENAI_COMPAT_API_KEY: ${OPENAI_COMPAT_API_KEY:-}
   DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
   QWEN_API_KEY: ${QWEN_API_KEY:-}
   ```
4. Create `.env.example` if it doesn't exist, documenting all variables.

**Verification:**
- `docker compose config` shows `${VARIABLE}` syntax, not hardcoded passwords.
- `docker compose up` still works with default values.

---

## Phase 2: Concurrency & Correctness

> 4 items. Fixes for race conditions and logic bugs. Should be done before any feature work.

---

### P2-01: Async Lock for TaskManager Persistence

**Complexity:** M
**Files:** `backend/services/task_manager.py`

**Context:** `_save_tasks()` performs blocking file I/O inside async functions. `self.tasks` dict mutations have no lock, so concurrent task creation can race on `self.task_counter`.

**Steps:**
1. Add `self._lock = asyncio.Lock()` in `__init__`.
2. Wrap all `self.tasks` mutations and `_save_tasks()` calls in `async with self._lock:`.
3. Convert `_save_tasks()` to async using `aiofiles` (already a dependency).
4. Similarly protect `self.task_counter` increments.

**Verification:**
- Create 10 tasks concurrently via `asyncio.gather` in a test → no duplicate IDs, no corrupted JSON.
- Existing tests pass.

---

### P2-02: Fix Shared LaTeX Compiler Attempts

**Complexity:** S
**Files:** `backend/services/task_manager.py` (line 52), `backend/services/latex_compiler.py`

**Context:** A single `LaTeXCompiler` instance is shared across all concurrent tasks. Its `self.attempts` list is mutated by every task — `clear_attempts()` wipes another task's history, `get_last_error()` returns wrong data.

**Steps:**
1. **Option A (simplest):** Create a new `LaTeXCompiler` instance per task execution instead of sharing one:
   ```python
   # In run_task / run_task_v3:
   compiler = LaTeXCompiler(max_retries=settings.max_latex_retries)
   ```
2. **Option B:** Make `attempts` a parameter passed through the compilation pipeline rather than instance state.
3. Remove `self.latex_compiler` from the `TaskManager.__init__`.

**Verification:**
- Run two tasks concurrently that both require LaTeX compilation → both succeed, no cross-contamination of error messages.

---

### P2-03: Deduplicate `_TaskCancelled` Exception

**Complexity:** S
**Files:** `backend/services/task_manager.py`

**Context:** Search for duplicate `_TaskCancelled` class definitions or inconsistent exception handling patterns within the task manager.

**Steps:**
1. Audit all custom exception classes in `task_manager.py`.
2. If `_TaskCancelled` is defined more than once, consolidate to a single definition.
3. Move it to `backend/models/` or `backend/exceptions.py` if it's used across files.

**Verification:**
- `grep -n "_TaskCancelled" backend/services/task_manager.py` shows exactly one class definition.
- Task cancellation still works correctly.

---

### P2-04: Parallelize Question Generation

**Complexity:** S
**Files:** `backend/services/task_manager.py`

**Context:** If application questions are generated sequentially (one LLM call per question), this creates unnecessary latency.

**Steps:**
1. Identify where question answers are generated.
2. If sequential, refactor to use `asyncio.gather()` for concurrent generation.
3. Respect the concurrency semaphore — don't spawn more parallel LLM calls than the provider allows.

**Verification:**
- Generate answers for 3 questions → total time is roughly 1x single-question time, not 3x.

---

## Phase 3: Developer Experience & Tooling

> 6 items. Sets up linting, formatting, and CI tooling that later phases depend on.

---

### P3-01: Create ESLint Flat Config

**Complexity:** M
**Files:** `frontend/eslint.config.js` (new), `frontend/package.json`

**Steps:**
1. Install ESLint 9+ and plugins:
   ```bash
   npm install -D eslint @eslint/js typescript-eslint eslint-plugin-react-hooks eslint-plugin-react-refresh
   ```
2. Create `frontend/eslint.config.js` with flat config:
   ```js
   import js from '@eslint/js';
   import tseslint from 'typescript-eslint';
   import reactHooks from 'eslint-plugin-react-hooks';
   import reactRefresh from 'eslint-plugin-react-refresh';

   export default tseslint.config(
     js.configs.recommended,
     ...tseslint.configs.recommended,
     {
       plugins: { 'react-hooks': reactHooks, 'react-refresh': reactRefresh },
       rules: {
         ...reactHooks.configs.recommended.rules,
         'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
         '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
       },
     },
     { ignores: ['dist/', 'node_modules/'] },
   );
   ```
3. Add `"lint": "eslint src/"` to `package.json` scripts.
4. Fix any errors surfaced by the initial run.

**Verification:**
- `npm run lint` exits 0.

---

### P3-02: Add Prettier Configuration

**Complexity:** S
**Files:** `frontend/.prettierrc` (new), `frontend/package.json`

**Steps:**
1. Install: `npm install -D prettier eslint-config-prettier`
2. Create `frontend/.prettierrc`:
   ```json
   {
     "semi": true,
     "singleQuote": true,
     "trailingComma": "all",
     "printWidth": 100,
     "tabWidth": 2
   }
   ```
3. Add Prettier's ESLint config to disable conflicting rules.
4. Add `"format": "prettier --write src/"` and `"format:check": "prettier --check src/"` to scripts.
5. Run `npm run format` once to normalize existing code.

**Verification:**
- `npm run format:check` exits 0.

---

### P3-03: Expand mypy Coverage Incrementally

**Complexity:** L
**Files:** `backend/mypy.ini`

**Context:** `ignore_errors = true` is set for `services.*`, `agents.*`, `api.*`, `middleware.*`, and `tests.*` — effectively disabling mypy for all production code.

**Steps:**
1. **Phase 3a:** Remove `ignore_errors = true` from `middleware.*` and `api.*` (smallest surface area).
2. Fix all resulting type errors.
3. **Phase 3b:** Remove from `agents.*` and fix errors.
4. **Phase 3c:** Remove from `services.*` (largest, most complex) and fix errors.
5. Keep `ignore_errors = true` for `tests.*` and `alembic.*` (low value to type-check).
6. Set `disallow_untyped_defs = true` globally once all sections pass.

**Verification:**
- `uv run mypy .` in `backend/` exits 0 (with only test/alembic ignores remaining).

---

### P3-04: Add Root Makefile

**Complexity:** S
**Files:** `Makefile` (new at repo root)

**Steps:**
1. Create `Makefile`:
   ```makefile
   .PHONY: dev dev-backend dev-frontend lint lint-backend lint-frontend test test-backend test-frontend build docker-build

   dev:
   	$(MAKE) dev-backend & $(MAKE) dev-frontend

   dev-backend:
   	cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 48765

   dev-frontend:
   	cd frontend && npm run dev

   lint: lint-backend lint-frontend

   lint-backend:
   	cd backend && uv run ruff check . && uv run ruff format --check .

   lint-frontend:
   	cd frontend && npm run lint && npm run format:check

   test: test-backend test-frontend

   test-backend:
   	cd backend && uv run pytest -m "not e2e and not integration"

   test-frontend:
   	cd frontend && npx vitest run

   build:
   	cd frontend && npm run build

   docker-build:
   	docker compose build
   ```

**Verification:**
- `make lint-backend` runs ruff.
- `make test-backend` runs pytest.

---

### P3-05: Add Dependabot Config

**Complexity:** S
**Files:** `.github/dependabot.yml` (new)

**Steps:**
1. Create `.github/dependabot.yml`:
   ```yaml
   version: 2
   updates:
     - package-ecosystem: "pip"
       directory: "/backend"
       schedule:
         interval: "weekly"
       open-pull-requests-limit: 5

     - package-ecosystem: "npm"
       directory: "/frontend"
       schedule:
         interval: "weekly"
       open-pull-requests-limit: 5

     - package-ecosystem: "docker"
       directory: "/backend"
       schedule:
         interval: "monthly"

     - package-ecosystem: "github-actions"
       directory: "/"
       schedule:
         interval: "weekly"
   ```

**Verification:**
- File passes YAML lint.
- Dependabot will start creating PRs once pushed to GitHub.

---

### P3-06: Add Docker Build to CI

**Complexity:** S
**Files:** `.github/workflows/ci.yml` (existing or new)

**Steps:**
1. Add a job to the CI workflow that runs `docker compose build`.
2. This catches Dockerfile syntax errors, missing files, and build failures early.
3. Example job:
   ```yaml
   docker-build:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       - run: docker compose build
   ```

**Verification:**
- CI pipeline includes Docker build step.
- A broken Dockerfile would fail CI.

---

## Phase 4: Frontend Architecture

> 7 items. Component decomposition, data fetching improvements, and polish.

---

### P4-01: Add React Error Boundary

**Complexity:** S
**Files:** `frontend/src/App.tsx`, `frontend/src/components/ErrorBoundary.tsx` (new)

**Steps:**
1. Create `ErrorBoundary.tsx` — a class component implementing `componentDidCatch` and `getDerivedStateFromError`.
2. Render a user-friendly fallback UI with a "Reload" button.
3. Wrap the main app content in `<ErrorBoundary>` in `App.tsx`.

**Verification:**
- Throw an error in a component → fallback UI appears instead of white screen.
- "Reload" button resets the error state.

---

### P4-02: Split `TaskPanel` into Sub-Components

**Complexity:** L
**Files:** `frontend/src/components/TaskPanel.tsx` (897 lines)

**Context:** TaskPanel is a monolithic 897-line component handling task creation form, status display, result viewing, PDF preview, LaTeX source, and agent progress. This hurts readability and makes targeted changes risky.

**Steps:**
1. Identify logical sections:
   - `TaskCreationForm.tsx` — JD input, company name, experience level, template selection, submit button.
   - `TaskStatusBar.tsx` — progress display, elapsed time, cancel/retry buttons.
   - `TaskResults.tsx` — resume/cover letter tabs, PDF preview, download buttons.
   - `LaTeXSourceView.tsx` — LaTeX source display and copy/download.
2. Extract each into its own file in `frontend/src/components/task/`.
3. `TaskPanel.tsx` becomes a thin orchestrator that renders the sub-components.
4. Pass shared state via props or create a `useTaskPanel` hook.

**Verification:**
- `npm run build` succeeds.
- All task panel functionality works identically (create, view status, view results, download).
- Total line count of `TaskPanel.tsx` drops below 200.

---

### P4-03: Refactor `SettingsPanel` with Data-Driven Rendering

**Complexity:** M
**Files:** `frontend/src/components/SettingsPanel.tsx` (1047 lines)

**Context:** SettingsPanel has repetitive blocks for each setting field. A data-driven approach would define settings as a schema and render them dynamically.

**Steps:**
1. Define a `SettingsSchema` array describing each field:
   ```ts
   type SettingField = {
     key: string;
     label: string;
     type: 'text' | 'password' | 'select' | 'number' | 'toggle';
     section: string;
     options?: { value: string; label: string }[];
     helpText?: string;
   };
   ```
2. Create a `SettingFieldRenderer` component that handles each field type.
3. Group fields by `section` and render dynamically.
4. Keep specialized sections (like provider testing) as dedicated components.

**Verification:**
- All settings are still editable and persist.
- `npm run build` succeeds.
- Line count drops significantly.

---

### P4-04: Unify Data Fetching (Remove Raw `fetch`)

**Complexity:** M
**Files:** `frontend/src/hooks/useTaskQuery.ts`, various components

**Context:** Some components use raw `fetch()` while others use `@tanstack/react-query`. This creates inconsistent loading states, error handling, and caching behavior.

**Steps:**
1. Audit all `fetch()` calls outside of react-query hooks.
2. Create dedicated query hooks for each data source (e.g., `useSettings`, `usePrompts`, `useCompanies`).
3. Replace raw `fetch()` calls with the new hooks.
4. Ensure all mutations go through `useMutation` with proper cache invalidation.

**Verification:**
- `grep -r "fetch(" frontend/src/ --include="*.tsx" --include="*.ts"` shows no raw fetch except in the query hook utility layer.
- All data fetching uses react-query.

---

### P4-05: Fix Untyped Query Hooks

**Complexity:** S
**Files:** `frontend/src/hooks/useTaskQuery.ts` (178 lines)

**Context:** Some react-query hooks may lack proper TypeScript generics, resulting in `any` types that defeat the purpose of TypeScript.

**Steps:**
1. Audit all `useQuery` / `useMutation` calls for explicit type parameters.
2. Add `<TData, TError>` generics where missing.
3. Ensure all `queryFn` return types are inferred or explicitly typed.
4. Fix any `as any` casts.

**Verification:**
- `npx tsc --noEmit` reports no type errors in hook files.

---

### P4-06: Add Code Splitting with `React.lazy`

**Complexity:** S
**Files:** `frontend/src/App.tsx`

**Steps:**
1. Lazy-load heavy components that aren't needed on initial render:
   ```tsx
   const SettingsPanel = React.lazy(() => import('./components/SettingsPanel'));
   const PromptsPanel = React.lazy(() => import('./components/PromptsPanel'));
   ```
2. Wrap lazy components in `<Suspense fallback={<Loading />}>`.
3. Ensure named exports are handled (may need to adjust imports).

**Verification:**
- Network tab shows separate chunks for settings/prompts panels.
- `npm run build` succeeds with code splitting.
- No visual regression — panels load smoothly with fallback.

---

### P4-07: Fix Dark Mode FOUC

**Complexity:** S
**Files:** `frontend/index.html`

**Context:** Dark mode is toggled via JavaScript at runtime, causing a flash of light-mode content on page load for users who prefer dark mode.

**Steps:**
1. Add a blocking inline script in `<head>` of `index.html`:
   ```html
   <script>
     (function() {
       var theme = localStorage.getItem('theme');
       if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
         document.documentElement.classList.add('dark');
       }
     })();
   </script>
   ```
2. This runs synchronously before any rendering, preventing the flash.

**Verification:**
- Set `localStorage.theme = 'dark'`, hard-reload → no flash of light mode.
- Set `localStorage.theme = 'light'`, hard-reload → no flash of dark mode.

---

## Phase 5: Backend Architecture

> 3 items. Code deduplication and configurability.

---

### P5-01: Deduplicate `generate_resume_with_error_feedback`

**Complexity:** M
**Files:** `backend/services/task_manager.py`

**Context:** The resume generation logic with error feedback / retry may be duplicated between v2 and v3 execution paths.

**Steps:**
1. Identify the shared logic between `run_task()` (v2) and `run_task_v3()`.
2. Extract common patterns into helper methods:
   - `_generate_and_compile_resume()` — handles LLM call → LaTeX → PDF pipeline.
   - `_handle_compilation_error()` — error feedback loop.
3. Both `run_task` and `run_task_v3` call the shared helpers.

**Verification:**
- Both v2 and v3 task execution still produce correct PDFs.
- DRY: the compilation retry logic exists in exactly one place.

---

### P5-02: Make Quality Threshold Configurable

**Complexity:** S
**Files:** `backend/agents/quality_gate.py`, `backend/config.py`

**Context:** `QUALITY_THRESHOLD = 0.7` and `MAX_RETRIES = 2` are hardcoded constants.

**Steps:**
1. Add to `config.py` Settings:
   ```python
   quality_threshold: float = 0.7
   quality_max_retries: int = 2
   ```
2. In `quality_gate.py`, read from settings instead of module-level constants.
3. Expose in the settings API so users can tune via the UI.

**Verification:**
- Set `QUALITY_THRESHOLD=0.5` via env var → lower-quality resumes pass the gate.
- Default behavior unchanged when env var is not set.

---

### P5-03: Clean Up `resume_validator` Sync/Async Split

**Complexity:** M
**Files:** `backend/services/resume_validator.py` (or similar)

**Context:** If the validator has a mix of sync and async methods, the async callers may be wrapping sync code with `run_in_executor`, adding complexity.

**Steps:**
1. Audit the validator for sync/async patterns.
2. If the core logic is CPU-bound (regex, parsing), keep it sync and call from async with `asyncio.to_thread()`.
3. If it makes I/O calls (LLM, file reads), make it properly async.
4. Remove any unnecessary `run_in_executor` wrappers.

**Verification:**
- Resume validation still works in both v2 and v3 pipelines.
- No blocking I/O in the async event loop.

---

## Phase 6: UX & Accessibility

> 3 items. User experience improvements and a11y compliance.

---

### P6-01: Add Delete Confirmation Dialog

**Complexity:** S
**Files:** `frontend/src/components/TaskSidebar.tsx`

**Context:** Task deletion is immediate with no confirmation. Accidental clicks can destroy results.

**Steps:**
1. Create a simple confirmation dialog component (or use `window.confirm` as MVP).
2. On delete click, show "Are you sure you want to delete this task? This cannot be undone."
3. Only proceed with deletion on confirmation.

**Verification:**
- Click delete → dialog appears.
- Cancel → task is preserved.
- Confirm → task is deleted.

---

### P6-02: Add ARIA Labels and Roles

**Complexity:** M
**Files:** Multiple frontend components

**Steps:**
1. Audit all interactive elements for missing ARIA attributes:
   - Buttons without text content need `aria-label`.
   - Icon-only buttons need `aria-label` describing the action.
   - Form inputs need associated `<label>` or `aria-label`.
   - Navigation sections need `role="navigation"` or `<nav>`.
   - Main content area needs `role="main"` or `<main>`.
   - Status messages need `role="status"` or `aria-live="polite"`.
2. Add `aria-label` to all icon-only buttons (lucide-react icons).
3. Add `role="status"` to toast notifications.
4. Ensure tab order is logical.

**Verification:**
- Run axe DevTools or Lighthouse accessibility audit → no critical violations.
- Screen reader can navigate all interactive elements.

---

### P6-03: Add Responsive Breakpoints

**Complexity:** L
**Files:** Multiple frontend components, `frontend/tailwind.config.js`

**Context:** The app may not render well on smaller screens (tablets, narrow browser windows).

**Steps:**
1. Audit the layout at 768px, 1024px, and 1280px widths.
2. Identify breakpoints where the sidebar/main panel layout should stack.
3. Add Tailwind responsive classes (`md:`, `lg:`) for:
   - Sidebar: collapse to top bar or hamburger menu on mobile.
   - TaskPanel: full-width on small screens.
   - SettingsPanel: single-column layout on mobile.
4. Test PDF preview at smaller sizes.

**Verification:**
- At 768px width: layout is usable, no horizontal scroll.
- At 1280px+: layout matches current design.

---

## Phase 7: Feature Enhancements (Deferred)

> 6 items. New features — implement in future sessions after foundational work is solid.

---

### P7-01: Expose Per-Agent Provider Overrides in UI

**Complexity:** M
**Files:** `frontend/src/components/SettingsPanel.tsx`, `backend/api/routes.py`, `backend/config.py`

**Description:** Allow users to select different LLM providers/models for each agent (researcher, writer, reviewer) via the settings UI.

---

### P7-02: Plain Text Export

**Complexity:** S
**Files:** `backend/api/routes.py`, `frontend/src/components/TaskPanel.tsx`

**Description:** Add a "Copy as Plain Text" button that strips LaTeX formatting and returns the resume as clean text.

---

### P7-03: JD Analysis Preview Before Generation

**Complexity:** M
**Files:** `frontend/src/components/TaskPanel.tsx`, `backend/api/routes.py`

**Description:** After pasting a JD, show an analysis preview (key skills, requirements, company info) before the user commits to generation.

---

### P7-04: Streaming AI Responses

**Complexity:** L
**Files:** Backend agents, WebSocket handler, frontend display

**Description:** Stream LLM output token-by-token to the frontend for real-time feedback during generation.

---

### P7-05: DOCX Export

**Complexity:** M
**Files:** `backend/services/`, `backend/api/routes.py`

**Description:** Generate Word documents in addition to PDF, using `python-docx`.

---

### P7-06: Resume Version History

**Complexity:** L
**Files:** Backend models, database, frontend UI

**Description:** Store multiple versions of generated resumes per task, allowing users to compare and revert.

---

## Phase 8: Infrastructure

> 2 items. Testing and automation infrastructure.

---

### P8-01: Add Frontend Test Coverage

**Complexity:** M
**Files:** `frontend/vitest.config.ts`, `frontend/src/**/*.test.tsx` (new files)

**Steps:**
1. Ensure Vitest is configured with React Testing Library:
   ```bash
   npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
   ```
2. Add `vitest.config.ts`:
   ```ts
   import { defineConfig } from 'vitest/config';
   export default defineConfig({
     test: {
       environment: 'jsdom',
       setupFiles: './src/test-setup.ts',
       globals: true,
     },
   });
   ```
3. Create `src/test-setup.ts` with `@testing-library/jest-dom` import.
4. Write tests for critical components:
   - `TaskSidebar.test.tsx` — renders task list, handles clicks.
   - `ErrorBoundary.test.tsx` — catches errors, shows fallback.
5. Add `"test": "vitest run"` to `package.json` scripts.

**Verification:**
- `npm test` runs and passes.
- At least 3 component tests exist.

---

### P8-02: Add Pre-Commit Hooks

**Complexity:** S
**Files:** `.pre-commit-config.yaml` (new), `backend/pyproject.toml`

**Steps:**
1. Create `.pre-commit-config.yaml`:
   ```yaml
   repos:
     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.8.0
       hooks:
         - id: ruff
           args: [--fix]
         - id: ruff-format

     - repo: https://github.com/pre-commit/mirrors-prettier
       rev: v4.0.0-alpha.8
       hooks:
         - id: prettier
           types_or: [javascript, typescript, tsx, css, json, yaml, markdown]
           args: [--config, frontend/.prettierrc]

     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v4.6.0
       hooks:
         - id: trailing-whitespace
         - id: end-of-file-fixer
         - id: check-yaml
         - id: check-added-large-files
           args: [--maxkb=500]
   ```
2. Add install instructions to README or Makefile: `pre-commit install`.

**Verification:**
- `pre-commit run --all-files` passes.
- A commit with a linting error is blocked by the hook.

---

## Appendix A: Dependency Graph

```
Phase 0 (Housekeeping) ──┐
Phase 1 (Security) ──────┤
Phase 2 (Concurrency) ───┼──→ Phase 4 (Frontend Architecture)
Phase 3 (DX & Tooling) ──┘         │
                                    ├──→ Phase 6 (UX & Accessibility)
                          Phase 5 (Backend Architecture) ──┘
                                    │
                          Phase 7 (Features) ← deferred
                          Phase 8 (Infrastructure) ← can parallelize with Phase 4-6
```

**Key dependencies:**
- P3-01 (ESLint) should complete before P4-* to catch issues early.
- P3-02 (Prettier) should complete before P8-02 (pre-commit hooks).
- P2-02 (LaTeX compiler fix) should complete before any task that exercises concurrent generation.
- P1-01 (input limits) should complete before P1-04 (API key auth).

---

## Appendix B: Files Index

| File | Phases | Changes |
|------|--------|---------|
| `.gitattributes` | P0-02 | Create |
| `.gitignore` | P0-01, P0-04 | Add `nul`, keep `uv.lock` uncommented |
| `.github/dependabot.yml` | P3-05 | Create |
| `.github/workflows/ci.yml` | P3-06 | Add Docker build job |
| `.pre-commit-config.yaml` | P8-02 | Create |
| `Makefile` | P3-04 | Create |
| `docker-compose.yml` | P1-07 | Externalize credentials |
| `backend/Dockerfile` | P1-06 | Add non-root user |
| `backend/api/routes.py` | P1-01 thru P1-05, P5-01 | Security, error handling |
| `backend/agents/quality_gate.py` | P5-02 | Configurable threshold |
| `backend/config.py` | P1-04, P5-02 | Auth key, quality settings |
| `backend/middleware/auth.py` | P1-04 | Create (API key auth) |
| `backend/middleware/rate_limit.py` | P1-03 | Apply per-route limits |
| `backend/models/task.py` | P1-01 | Add Field max_length |
| `backend/mypy.ini` | P3-03 | Remove ignore_errors |
| `backend/pyproject.toml` | P0-05 | Version bump |
| `backend/requirements.txt` | P0-03 | Delete |
| `backend/services/latex_compiler.py` | P2-02 | Fix shared state |
| `backend/services/task_manager.py` | P2-01, P2-03, P2-04, P5-01 | Locks, dedup |
| `backend/services/resume_validator.py` | P5-03 | Sync/async cleanup |
| `frontend/eslint.config.js` | P3-01 | Create |
| `frontend/.prettierrc` | P3-02 | Create |
| `frontend/index.html` | P4-07 | Dark mode FOUC fix |
| `frontend/package.json` | P0-05, P0-06 | Version bump, remove dead deps |
| `frontend/src/App.tsx` | P4-01, P4-06 | Error boundary, lazy loading |
| `frontend/src/components/AgentProgress.tsx` | P0-07 | Delete (if unused) |
| `frontend/src/components/ErrorBoundary.tsx` | P4-01 | Create |
| `frontend/src/components/TaskPanel.tsx` | P4-02 | Decompose |
| `frontend/src/components/SettingsPanel.tsx` | P4-03 | Data-driven refactor |
| `frontend/src/components/TaskSidebar.tsx` | P6-01 | Delete confirmation |
| `frontend/src/hooks/useTaskQuery.ts` | P4-04, P4-05 | Typed hooks, unify fetch |
| `frontend/vitest.config.ts` | P8-01 | Create |
