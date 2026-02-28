# Blueprint for a production-grade AI resume generator

**LangGraph 1.0, agentic RAG, and a modern React frontend form the backbone of a portfolio project that demonstrates genuine AI engineering depth.** This implementation plan covers every layer — from multi-agent orchestration to CI/CD — with specific library versions, code patterns, and architectural decisions current as of early 2025. The project's architecture (FastAPI + React + Gemini + LaTeX) already has solid bones; the improvements below transform it from a functional prototype into a system that showcases RAG, agent pipelines, structured evaluation, and full-stack polish — exactly what hiring managers look for in AI software engineer candidates.

---

## 1. LangGraph multi-agent pipeline is the architectural centerpiece

LangGraph **v1.0.7** (reached 1.0 on October 17, 2025) is now the official LangChain recommendation for all new agent implementations. For this resume generator, a **StateGraph with conditional edges** — not CrewAI, not raw LangChain — is the optimal pattern. It gives you typed state management, retry loops, conditional routing, and human-in-the-loop support without the abstraction overhead of CrewAI's role-based metaphor.

### State definition and graph structure

Define a single `ResumeState` using `TypedDict` that flows through four sequential agents with quality-gated routing:

```python
from typing import TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class ResumeState(TypedDict, total=False):
    job_description: str
    user_resume_data: dict
    generate_cover_letter: bool
    jd_analysis: dict          # JD Analyzer output
    relevance_matches: dict    # Relevance Matcher output
    relevance_score: float
    generated_resume: dict     # Resume Generator output
    resume_quality_score: float
    generated_cover_letter: Optional[dict]
    current_step: str
    error_count: int
```

The pipeline flows as: **JD Analyzer → Relevance Matcher → Resume Generator → (quality gate) → Cover Letter Agent → Finalize**. The quality gate is the key differentiator — a conditional edge that routes back to the Resume Generator if the quality score falls below 0.7, up to two retries:

```python
def quality_check_router(state: ResumeState) -> str:
    if state.get("resume_quality_score", 0) < 0.7:
        if state.get("error_count", 0) >= 2:
            return "finalize"      # Accept after max retries
        return "retry_resume"
    if state.get("generate_cover_letter", False):
        return "cover_letter"
    return "finalize"

builder = StateGraph(ResumeState)
builder.add_node("jd_analyzer", jd_analyzer_agent)
builder.add_node("relevance_matcher", relevance_matching_agent)
builder.add_node("resume_generator", resume_generation_agent)
builder.add_node("cover_letter", cover_letter_agent)
builder.add_node("finalize", finalize_node)
builder.add_node("retry_resume", lambda s: {
    "error_count": s.get("error_count", 0) + 1
})

builder.add_edge(START, "jd_analyzer")
builder.add_edge("jd_analyzer", "relevance_matcher")
builder.add_edge("relevance_matcher", "resume_generator")
builder.add_conditional_edges("resume_generator", quality_check_router, {
    "retry_resume": "retry_resume",
    "cover_letter": "cover_letter",
    "finalize": "finalize",
})
builder.add_edge("retry_resume", "resume_generator")
builder.add_edge("cover_letter", "finalize")
builder.add_edge("finalize", END)

graph = builder.compile()
```

### Pydantic structured outputs enforce schema discipline

Each agent should produce typed, validated output. Gemini 2.0 supports Pydantic schemas natively through `response_schema`:

```python
from google import genai
from pydantic import BaseModel, Field

class JDAnalysis(BaseModel):
    job_title: str = Field(description="Extracted job title")
    required_skills: list[str] = Field(description="Required technical skills")
    preferred_skills: list[str] = Field(description="Nice-to-have skills")
    experience_years: int = Field(description="Minimum years of experience")
    key_responsibilities: list[str]
    company_name: str | None = Field(default=None)

client = genai.Client(api_key="...")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=f"Analyze this job description: {jd_text}",
    config={
        "response_mime_type": "application/json",
        "response_schema": JDAnalysis,
    },
)
result = JDAnalysis.model_validate_json(response.text)
```

For LangGraph integration specifically, use `langchain-google-genai`'s `with_structured_output`:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
structured_llm = llm.with_structured_output(JDAnalysis)
result = structured_llm.invoke("Analyze this JD: ...")
```

**Important gotcha**: Gemini sometimes omits optional fields rather than setting them to `None`, causing Pydantic v2 `ValidationError`. Always use `Field(default=None)` on optional fields and implement a retry wrapper that appends validation errors to the prompt on failure.

### Why LangGraph over the alternatives

**LangGraph** beats CrewAI for this use case because your pipeline is deterministic and sequential — you don't need autonomous agent negotiation. CrewAI's role-based abstraction adds overhead without benefit here and makes debugging harder. Plain LangChain lacks built-in cycle/retry support and state management. LangGraph's built-in `RetryPolicy`, conditional edges, and checkpointing (via `PostgresSaver` for production) map directly to resume generation requirements. It's also used in production by Uber, LinkedIn, and Replit — strong portfolio signal.

**Recommended packages**:
```
langgraph>=1.0.0,<2.0.0
langgraph-prebuilt>=1.0.0
langchain-core>=0.3.0
langchain-google-genai>=2.1.0
pydantic>=2.0
```

### FastAPI integration with streaming

Expose the graph via FastAPI, using `astream` with `stream_mode="updates"` to push real-time progress to the React frontend:

```python
@app.post("/api/generate-resume/stream")
async def stream_resume(request: ResumeRequest):
    initial_state = {
        "job_description": request.job_description,
        "user_resume_data": request.user_data,
        "generate_cover_letter": request.include_cover_letter,
        "error_count": 0,
    }
    async def event_generator():
        async for delta in graph.astream(initial_state, stream_mode="updates"):
            yield f"data: {json.dumps(delta)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 2. A lightweight RAG pipeline grounds resumes in real company context

The RAG system scrapes company information, chunks and indexes it, then injects relevant context into the Resume and Cover Letter agents. This is where the "AI engineer" differentiation happens — moving from generic LLM output to company-tailored content.

### Vector store and embedding model selection

For a personal portfolio project, **ChromaDB** is the right starting point — it installs with `pip install chromadb`, requires zero infrastructure, and its **2025 Rust rewrite delivers 4x faster writes/queries** than the original Python implementation. If you later want to demonstrate production awareness, add Qdrant as an alternative backend with its superior metadata filtering.

For embeddings, **BGE-M3** (BAAI) is the best free option: **63.0 MTEB score**, MIT license, 8192-token context, and it supports dense + sparse + multi-vector retrieval in a single model. If you prefer a paid API for simplicity, **OpenAI text-embedding-3-small** at $0.02/M tokens is extremely affordable.

```python
# BGE-M3 (free, local)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-m3')
embeddings = model.encode(["Company description text..."])

# Or OpenAI (cheap, no GPU needed)
from openai import OpenAI
client = OpenAI()
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Company description text..."
)
```

### Web scraping with Firecrawl and BeautifulSoup

Use **Firecrawl** as the primary scraping tool — it converts pages to clean markdown (LLM-ready), handles JavaScript-rendered career pages, and supports Pydantic schema extraction natively:

```python
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key='...')
result = app.scrape_url('https://company.com/careers', {
    'formats': [{'type': 'json', 'prompt': 'Extract job requirements, tech stack, and company culture'}]
})
```

Keep **BeautifulSoup + httpx** as a free fallback for simple static pages. Always check `robots.txt`, implement rate limiting (1-2 requests/second), and never store personal data without consent.

### Chunking strategy and metadata enrichment

Use **RecursiveCharacterTextSplitter** with **500 tokens and 15% overlap** — NVIDIA research shows this combination achieves **88-89% retrieval recall** for factoid queries like job descriptions:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, chunk_overlap=75,
    separators=["\n\n", "\n", ". ", " ", ""],
)
chunks = splitter.split_documents(docs)
for chunk in chunks:
    chunk.metadata.update({
        "source_type": "careers",       # about_page, news, job_description
        "company_name": "Acme Corp",
        "content_type": "tech_stack",   # culture, requirements, benefits
        "scraped_date": "2025-01-15",
    })
```

Metadata isn't an afterthought — it's a first-class filtering signal. Tag every chunk with `source_type`, `company_name`, `content_type`, and `scraped_date` so the retrieval agent can filter precisely.

### Integrating RAG into the LangGraph pipeline

Create a retrieval tool that the JD Analyzer or Cover Letter agent can call. LangGraph's **Agentic RAG** pattern adds document grading — if retrieved documents are irrelevant, it rewrites the query and retries:

```python
from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

@tool
def retrieve_company_info(query: str) -> str:
    """Search company knowledge base for context."""
    docs = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])

# Add as a tool node in the graph
builder.add_node("retrieve", ToolNode([retrieve_company_info]))
```

The recommended pattern is **Corrective RAG**: retrieve → grade documents for relevance → if poor, rewrite query → retrieve again → generate. This adds **<50ms overhead** from graph coordination; real latency comes from LLM calls (2-5 seconds typical).

---

## 3. Automated evaluation closes the quality loop

Building a scoring framework that evaluates resume quality programmatically is what separates this project from basic LLM wrappers. Implement two layers: deterministic ATS scoring and LLM-as-a-judge evaluation.

### Deterministic ATS keyword scoring

Combine **spaCy NER + TF-IDF cosine similarity** for a fast, reproducible baseline:

```python
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nlp = spacy.load("en_core_web_sm")

def keyword_match_score(resume_keywords: set, jd_keywords: set) -> dict:
    matched = resume_keywords & jd_keywords
    missing = jd_keywords - resume_keywords
    score = len(matched) / len(jd_keywords) if jd_keywords else 0
    return {
        "score": score,
        "matched_keywords": list(matched),
        "missing_keywords": list(missing),
        "coverage_percentage": score * 100,
    }

def compute_similarity(resume_text: str, jd_text: str) -> float:
    vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words='english')
    tfidf = vectorizer.fit_transform([resume_text, jd_text])
    return cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
```

Weight your scoring: **40% keyword match**, **20% experience alignment**, **10% format compliance**, **10% action verbs**, **10% readability**, **10% section completeness**. Industry ATS thresholds: ≥80% means interview likely, <50% means auto-rejection.

### LLM-as-a-judge with DeepEval

**DeepEval** is the recommended framework for LLM evaluation in 2025 — it integrates with pytest, supports custom G-Eval rubrics, and avoids the NaN scoring issues that plague RAGAS:

```python
from deepeval.metrics import GEval

resume_quality_metric = GEval(
    name="Resume Quality",
    criteria="""Evaluate on: 1) Keyword alignment with JD (0-1),
    2) Professional tone and action verbs (0-1),
    3) Quantified achievements (0-1),
    4) Relevance of highlighted experience (0-1),
    5) ATS formatting compliance (0-1)""",
    evaluation_params=["input", "actual_output"],
    model="gpt-4.1",
    threshold=0.7,
)
```

### Self-critique loop in LangGraph

The most impressive pattern: wire the evaluation directly into the pipeline as a feedback loop. After resume generation, an evaluation node scores the output. If the score is below threshold, the graph routes back to generation with specific improvement feedback, up to **3 iterations**:

```
generate_resume → evaluate_resume → [score >= 4.0 or iteration >= 3?]
    → YES: finalize
    → NO: revise_resume (with feedback) → evaluate_resume
```

Best practices: use **low-precision scales** (1-5 or binary) for consistency, always include chain-of-thought reasoning before scores, and limit to **5 metrics maximum** per evaluation pass to avoid noise.

---

## 4. Database schema captures the full generation lifecycle

### SQLAlchemy 2.0 async is the production choice

**SQLAlchemy 2.0.46** with `asyncpg` is the gold standard async ORM for FastAPI in 2025 — most mature, highest performance in benchmarks, and massive ecosystem. **SQLModel** (by FastAPI's creator) is a viable alternative that reduces boilerplate by unifying Pydantic and SQLAlchemy models, but it has a single-maintainer risk. For maximum portfolio impressiveness, use SQLAlchemy directly.

```
sqlalchemy[asyncio]>=2.0.14
asyncpg>=0.29.0
alembic>=1.13.0
```

### Schema design for resume version control

The schema needs five core tables: users, profiles, resume versions, generation tasks, and LLM metrics.

```sql
CREATE TABLE resume_versions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content JSONB,              -- Structured resume sections
    latex_source TEXT,          -- Raw LaTeX for re-compilation
    pdf_url VARCHAR,            -- S3/storage path
    is_current BOOLEAN DEFAULT FALSE,
    parent_version_id UUID REFERENCES resume_versions(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, version_number)
);

CREATE TABLE llm_generation_metadata (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES generation_tasks(id),
    agent_name VARCHAR,         -- 'jd_analyzer', 'resume_writer', etc.
    model_name VARCHAR NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms INTEGER,
    cost_usd DECIMAL(10,6),
    input_hash VARCHAR,         -- For caching/deduplication
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Key design decisions: `parent_version_id` creates a linked-list/tree structure for version history, `JSONB` with GIN indexes enables querying within resume content, and `llm_generation_metadata` tracks per-agent token usage and latency — essential for cost optimization and debugging. Use **Alembic with async mode** (`alembic init -t async alembic`) and always run `alembic upgrade head` before starting the FastAPI server in Docker.

---

## 5. The frontend stack that signals modern engineering taste

### Component library and state management

The 2025 consensus frontend stack is **Vite + React 18/19 + shadcn/ui + Tailwind v4 + Zustand + TanStack Query**. This combination is what interviewers expect to see.

**shadcn/ui** (83K+ GitHub stars) is the dominant component library — it's built on Radix UI + Tailwind, uses a copy-paste model so you own the code, and looks polished out of the box. Initialize with `npx shadcn@latest init` and add components as needed.

The critical architectural insight that impresses interviewers: **separate client state from server state**. Use **Zustand** (~5kb) for UI state (active resume, sidebar toggle, theme) and **TanStack Query** (~13kb) for all API data with automatic caching, background refetching, and optimistic updates. Combined they're ~18kb versus Redux/Apollo's 50kb+.

For forms, **React Hook Form + Zod** is non-negotiable — Zod schemas provide runtime validation with TypeScript inference, and they can be shared between frontend and backend.

React Server Components are **not relevant** for this project since you have a separate FastAPI backend. Stick with Vite SPA; if asked about RSC in interviews, explain the deliberate architectural choice.

### PDF preview, charts, and diff views

Three specific libraries complete the resume-specific UI:

- **`react-pdf` v10** (by wojtekmaj) renders server-generated PDFs inline. It wraps Mozilla's PDF.js and accepts URLs, base64, or Uint8Array — ideal for displaying LaTeX-compiled PDFs from FastAPI.

- **Recharts v2** (24.8K stars) provides the declarative radar charts perfect for skill-matching visualization. Its `RadarChart` component overlays "Your Resume" vs "Job Requirements" scores, and the `BarChart` handles keyword coverage displays.

- **`react-diff-viewer-continued` v4.1.2** (the actively maintained fork) shows side-by-side or inline diffs of resume versions with word-level highlighting and dark mode support.

### WebSocket streaming with RAF batching

For real-time multi-agent progress, use native WebSocket with a **requestAnimationFrame buffer** — this prevents render thrashing when receiving 20+ tokens/second from LLM streaming:

```tsx
const flush = () => {
    if (bufferRef.current.length > 0) {
        setMessages(prev => [...prev, ...bufferRef.current]);
        bufferRef.current = [];
    }
    rafId = requestAnimationFrame(flush);
};

ws.onmessage = (event) => {
    bufferRef.current.push(JSON.parse(event.data));
};
```

Build a pipeline progress component that shows each agent's status (pending → running → complete) using animated pill indicators — this gives users confidence during the 10-20 second generation process.

---

## 6. DevOps that proves professional engineering habits

### GitHub Actions with uv, ruff, and mypy

Use **`uv`** (Astral's fast Python package manager) instead of pip/poetry — it's dramatically faster and represents the 2025 Python tooling consensus. Your CI pipeline should run four parallel jobs:

```yaml
# Backend: ruff lint + format check, mypy --strict, pytest with coverage
- run: uv run ruff check --output-format=github .
- run: uv run ruff format --check .
- run: uv run mypy --strict .
- run: uv run pytest -v --cov=src --cov-report=xml --cov-fail-under=80

# Frontend: ESLint, TypeScript type check, Vitest
- run: npx eslint . --max-warnings=0
- run: npx tsc --noEmit
- run: npx vitest run --coverage
```

Use **path filters** in a monorepo so `backend/**` changes only trigger Python CI and `frontend/**` changes only trigger TypeScript CI. Add a `bandit` security scan and Codecov badge on the README.

**Key versions**: `ruff>=0.14.0`, `mypy>=1.15.0`, `pytest>=8.3.5`, `pytest-asyncio>=1.0.0`, Node 22.

### Docker multi-stage builds

The docker-compose setup needs four services: FastAPI backend, React frontend, PostgreSQL, and LaTeX compilation. For LaTeX in Docker, install **only the packages you need** (`texlive-latex-base texlive-latex-extra texlive-fonts-recommended`) to keep the image at ~500MB rather than the full 4GB texlive distribution. Use multi-stage builds: a builder stage with `uv` for dependency installation, and a slim production stage that copies the `.venv`:

```dockerfile
FROM python:3.13-slim AS builder
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.13-slim AS production
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base texlive-latex-extra texlive-fonts-recommended
COPY --from=builder /app/.venv /app/.venv
```

### Conventional commits and git hygiene

Enforce **conventional commits** (`feat(api):`, `fix(latex):`, `test(agents):`) with `commitlint` + `husky` git hooks. Even for a solo project, create feature branches (`feat/resume-generation`, `refactor/async-db`) and squash-merge via PRs. What makes git history impressive to recruiters: consistent commit format, atomic commits, descriptive PR descriptions, GitHub Issues/Projects for tracking work, and **CI/CD badges on the README** showing build status and coverage percentage.

---

## 7. Testing strategy targets 80% coverage at the right layers

### Mocking LLM calls effectively

The core challenge is testing LLM-dependent code without hitting APIs. Use **`unittest.mock.patch`** as the primary approach, with **VCR-style cassette recording** via `pytest-recording` for integration tests that replay real API responses:

```python
@patch("google.generativeai.GenerativeModel.generate_content_async")
@pytest.mark.asyncio
async def test_resume_generation(mock_generate, sample_profile):
    mock_generate.return_value = MagicMock(
        text='{"summary": "Experienced developer..."}'
    )
    result = await generate_resume(sample_profile)
    assert "summary" in result
    mock_generate.assert_called_once()
```

For LangGraph pipelines, use **LangChain's `GenericFakeChatModel`** to inject deterministic responses during testing. Always validate that LLM outputs conform to Pydantic schemas — a failing `model_validate_json` call should be a test failure, not a runtime error.

### Integration testing and the test pyramid

Test the LangGraph pipeline at three levels. **Unit tests** (~60%) cover individual agent nodes with mocked LLMs. **Integration tests** (~25%) verify graph traversal order and conditional routing by checking the sequence of nodes visited. **End-to-end tests** (~15%) use VCR cassettes to replay full pipeline runs:

```python
@pytest.mark.vcr(cassette_library_dir="tests/cassettes")
@pytest.mark.asyncio
async def test_full_pipeline():
    result = await resume_pipeline.ainvoke({
        "user_profile": sample_profile,
        "job_description": sample_jd,
    })
    assert result["status"] == "completed"
    assert result["resume_quality_score"] >= 0.7
```

For WebSocket testing, FastAPI's `TestClient` supports synchronous WebSocket connections directly — verify that progress messages arrive in the correct sequence and contain expected fields.

### Coverage targets

Aim for **≥80% overall line coverage** with `--cov-fail-under=80` in CI. This is the sweet spot: high enough to demonstrate engineering discipline, not so high that you waste time covering trivial code. Target **≥90% on core business logic** (pipeline orchestration, generation, API endpoints) and **≥70% on infrastructure** (config, DB setup). Display the coverage badge prominently on the README.

---

## Conclusion

The implementation plan prioritizes three things that matter most for an AI engineer portfolio: **agent orchestration depth** (LangGraph pipeline with quality-gated retries and structured outputs), **RAG integration** (company research retrieval woven into the generation flow), and **evaluation rigor** (dual-layer scoring with deterministic ATS metrics and LLM-as-a-judge self-critique loops). The frontend, DevOps, and testing layers aren't afterthoughts — shadcn/ui + Zustand + TanStack Query, Docker multi-stage builds, and 80% test coverage all signal production-mindedness. The most impactful single addition is the self-critique loop: generate → evaluate → revise creates a visible, explainable quality improvement cycle that directly demonstrates your understanding of building reliable AI systems. Start there, then layer in RAG and the frontend polish.

### Full recommended tech stack at a glance

| Layer | Technology | Version |
|-------|-----------|---------|
| Agent orchestration | LangGraph | ≥1.0.0 |
| LLM provider | Gemini 2.0 Flash | Latest |
| Structured outputs | Pydantic v2 + native Gemini schema | ≥2.0 |
| Vector store | ChromaDB (dev) / Qdrant (prod) | Latest |
| Embeddings | BGE-M3 (free) or OpenAI text-embedding-3-small | Latest |
| Web scraping | Firecrawl + BeautifulSoup fallback | Latest |
| ATS scoring | spaCy + scikit-learn TF-IDF | spaCy 3.x |
| LLM evaluation | DeepEval + custom G-Eval rubrics | Latest |
| Backend ORM | SQLAlchemy 2.0 async + asyncpg | ≥2.0.14 |
| Migrations | Alembic (async mode) | ≥1.13.0 |
| Frontend framework | React + TypeScript + Vite | React 18/19, Vite 6.x |
| UI components | shadcn/ui (Radix + Tailwind v4) | Latest |
| Client state | Zustand | 5.x |
| Server state | TanStack Query | 5.x |
| Forms | React Hook Form + Zod | RHF 7.x, Zod 3.x |
| PDF preview | react-pdf | 10.x |
| Charts | Recharts | 2.x |
| Diff view | react-diff-viewer-continued | 4.x |
| Python tooling | uv + ruff + mypy | ruff ≥0.14, mypy ≥1.15 |
| Testing | pytest + DeepEval + VCR cassettes | pytest ≥8.3.5 |
| CI/CD | GitHub Actions | v4 actions |
| Containers | Docker multi-stage + docker-compose | Latest |