import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration - Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-pro-preview"  # Gemini 3 Pro (recommended)

    # Gemini Generation Parameters
    gemini_temperature: float | None = None
    gemini_top_k: int | None = None
    gemini_top_p: float | None = None
    gemini_max_output_tokens: int | None = None
    gemini_thinking_level: str = "high"

    # Google Search Grounding
    gemini_enable_search: bool = False

    # API Configuration - Claude (Anthropic)
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"

    # API Configuration - OpenAI-Compatible Proxy
    openai_compat_api_key: str = ""
    openai_compat_base_url: str = "http://localhost:3000/v1"
    openai_compat_model: str = "gpt-4o"

    # API Configuration - Claude Code Proxy
    claude_proxy_api_key: str = ""
    claude_proxy_base_url: str = "http://localhost:42069"
    claude_proxy_model: str = "claude-sonnet-4-5-20250929"

    # API Configuration - DeepSeek
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # API Configuration - Qwen (Alibaba DashScope)
    qwen_api_key: str = ""
    qwen_model: str = "qwen-plus"

    # Retry Configuration
    max_latex_retries: int = 3

    # Concurrency
    max_concurrent_tasks: int = 3

    # File Paths
    base_dir: Path = Path(__file__).parent
    prompts_dir: Path = base_dir / "prompts"
    output_dir: Path = base_dir / "output"
    logs_dir: Path = base_dir / "logs"
    responses_dir: Path = base_dir / "responses"
    templates_dir: Path = base_dir / "templates"
    data_dir: Path = base_dir / "data"

    # Database Configuration
    database_url: str = ""  # e.g. "postgresql+asyncpg://user:pass@localhost:5432/resume_gen"
    database_echo: bool = False  # Log SQL queries

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 48765
    frontend_port: int = 45173

    # PDF Generation Settings
    cover_letter_font: str = "Helvetica"
    cover_letter_font_size: int = 11
    cover_letter_font_zh: str = "SimSun"
    cover_letter_font_zh_fallback: str = "Helvetica"

    # Logging Configuration
    log_level: str = "INFO"
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Ensure directories exist
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)
settings.responses_dir.mkdir(parents=True, exist_ok=True)
settings.templates_dir.mkdir(parents=True, exist_ok=True)
settings.data_dir.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """Configure logging to both file and console."""
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Main log file handler (rotating)
    main_log_file = settings.logs_dir / "app.log"
    file_handler = RotatingFileHandler(
        main_log_file, maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Error log file handler (separate file for errors)
    error_log_file = settings.logs_dir / "error.log"
    error_handler = RotatingFileHandler(
        error_log_file, maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # Task-specific log file (for task processing details)
    task_log_file = settings.logs_dir / "tasks.log"
    task_handler = RotatingFileHandler(
        task_log_file, maxBytes=settings.log_max_bytes, backupCount=settings.log_backup_count, encoding="utf-8"
    )
    task_handler.setLevel(logging.INFO)
    task_handler.setFormatter(detailed_formatter)

    # Add task handler to specific loggers
    task_logger = logging.getLogger("services.task_manager")
    task_logger.addHandler(task_handler)

    gemini_logger = logging.getLogger("services.gemini_client")
    gemini_logger.addHandler(task_handler)

    return root_logger


# Initialize logging
logger = setup_logging()
logger.info(f"Logging initialized. Logs directory: {settings.logs_dir}")
