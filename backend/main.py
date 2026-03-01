import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from api.websocket import manager, progress_callback

# Import config first to initialize logging
from config import settings
from services.task_manager import task_manager

# Get logger after config initializes logging
logger = logging.getLogger(__name__)


def validate_environment():
    """Run startup checks and log warnings for missing dependencies."""
    warnings = []

    # Check pdflatex
    if not shutil.which("pdflatex"):
        warnings.append(
            "pdflatex not found in PATH. LaTeX compilation will fail. Install MiKTeX (Windows) or texlive (Linux/Mac)."
        )

    # Check API key for the default provider
    from services.settings_manager import get_settings_manager

    sm = get_settings_manager()
    default_provider = sm.get("default_provider") or "gemini"

    if default_provider == "gemini":
        api_key = sm.get("gemini_api_key") or settings.gemini_api_key
        if not api_key or api_key == "your_gemini_api_key_here":
            warnings.append("Gemini API key not configured. Set it in Settings or backend/.env")
    elif default_provider == "claude":
        api_key = sm.get("claude_api_key") or getattr(settings, "claude_api_key", "")
        if not api_key:
            warnings.append("Claude API key not configured. Set it in Settings or backend/.env")
    elif default_provider == "openai_compat":
        # OpenAI-compat may not need an API key (local proxy)
        pass

    # Check prompt files
    from services.prompt_manager import get_prompt_manager

    pm = get_prompt_manager()
    prompts = pm.get_all_prompts()
    for key, content in prompts.items():
        if not content.strip():
            warnings.append(f"Prompt '{key}' is empty. Edit it in the Prompts panel.")

    # Check required placeholders in resume prompt
    resume_prompt = prompts.get("resume_prompt", "")
    for placeholder in ["{{user_information}}", "{{latex_template}}", "{{JOB_DESCRIPTION}}"]:
        if placeholder not in resume_prompt:
            warnings.append(f"Resume prompt is missing placeholder {placeholder}")

    for w in warnings:
        logger.warning(f"STARTUP CHECK: {w}")

    if not warnings:
        logger.info("All startup checks passed")

    return warnings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("=" * 60)
    logger.info("Resume & Cover Letter Generator Starting")
    logger.info(f"Model: {settings.gemini_model}")
    logger.info(f"Output directory: {settings.output_dir}")
    logger.info(f"Logs directory: {settings.logs_dir}")
    logger.info(f"Responses directory: {settings.responses_dir}")
    logger.info("=" * 60)

    validate_environment()

    # Initialize database if configured (sqlalchemy is optional)
    _close_db = None
    try:
        from db.session import close_db, init_db

        await init_db()
        _close_db = close_db
    except ImportError:
        logger.info("SQLAlchemy not installed - database features disabled")

    yield

    if _close_db:
        await _close_db()
    logger.info("Resume & Cover Letter Generator Shutting Down")


app = FastAPI(
    title="Resume & Cover Letter Generator",
    description="Automated resume and cover letter generation with multi-provider AI support",
    version="3.0.0",
    lifespan=lifespan,
)

# Rate limiting (optional - requires slowapi)
from middleware.rate_limit import setup_rate_limiting

setup_rate_limiting(app)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.frontend_port}",
        f"http://127.0.0.1:{settings.frontend_port}",
        "http://localhost:3000",  # Docker/production
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register progress callback
task_manager.register_progress_callback(progress_callback)

# Include REST routes
app.include_router(router)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info(f"WebSocket client connected from {websocket.client}")
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from services.settings_manager import get_settings_manager

    sm = get_settings_manager()
    default_provider = sm.get("default_provider") or "gemini"
    return {
        "status": "healthy",
        "default_provider": default_provider,
        "model": settings.gemini_model,
        "pdflatex_available": shutil.which("pdflatex") is not None,
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server via uvicorn")
    uvicorn.run(app, host=settings.host, port=settings.port)
