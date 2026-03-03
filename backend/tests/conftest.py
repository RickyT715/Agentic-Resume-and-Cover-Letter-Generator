"""Shared fixtures for tests."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend is on sys.path
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def tmp_prompts_dir(tmp_path):
    """Create a temp prompts directory with all required prompt files."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "Resume_prompts.txt").write_text(
        "Resume prompt {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}", encoding="utf-8"
    )
    (prompts_dir / "Cover_letter_prompt.txt").write_text(
        "Cover letter {{RESUME_CONTENT}} {{JOB_DESCRIPTION}}", encoding="utf-8"
    )
    (prompts_dir / "User_information_prompts.txt").write_text(
        "I am a software engineer with 5 years of experience.", encoding="utf-8"
    )
    (prompts_dir / "Resume_format_prompts.txt").write_text("\\documentclass{article}", encoding="utf-8")
    (prompts_dir / "Application_question_prompt.txt").write_text(
        "Answer: {{USER_INFORMATION}} JD: {{JOB_DESCRIPTION}} Q: {{QUESTION}} Limit: {{WORD_LIMIT}}",
        encoding="utf-8",
    )
    # No-fabrication variant prompt files (EN)
    (prompts_dir / "Resume_prompts_no_fabrication.txt").write_text(
        "Resume no-fabrication {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}} Only use verified facts.",
        encoding="utf-8",
    )
    (prompts_dir / "Cover_letter_prompt_no_fabrication.txt").write_text(
        "Cover letter no-fabrication {{RESUME_CONTENT}} {{JOB_DESCRIPTION}} No invented details.",
        encoding="utf-8",
    )
    (prompts_dir / "Application_question_prompt_no_fabrication.txt").write_text(
        "Answer no-fabrication: {{USER_INFORMATION}} JD: {{JOB_DESCRIPTION}} Q: {{QUESTION}} Limit: {{WORD_LIMIT}} Only real facts.",
        encoding="utf-8",
    )
    # No-summary format templates
    (prompts_dir / "Resume_format_no_summary.txt").write_text(
        "\\documentclass{article}\n% No Summary section\n\\section{Education}", encoding="utf-8"
    )
    (prompts_dir / "Resume_format_no_summary_zh.txt").write_text(
        "\\documentclass{article}\\usepackage{xeCJK}\n% 无个人总结\n\\section{教育背景}", encoding="utf-8"
    )
    # Chinese prompt files
    (prompts_dir / "Resume_prompts_zh.txt").write_text(
        "中文简历 {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}", encoding="utf-8"
    )
    (prompts_dir / "Resume_prompts_no_fabrication_zh.txt").write_text(
        "中文简历禁止虚构 {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}} 仅使用真实信息。",
        encoding="utf-8",
    )
    (prompts_dir / "Cover_letter_prompt_zh.txt").write_text(
        "中文求职信 {{RESUME_CONTENT}} {{JOB_DESCRIPTION}}", encoding="utf-8"
    )
    (prompts_dir / "Cover_letter_prompt_no_fabrication_zh.txt").write_text(
        "中文求职信禁止虚构 {{RESUME_CONTENT}} {{JOB_DESCRIPTION}} 不编造细节。",
        encoding="utf-8",
    )
    (prompts_dir / "User_information_prompts_zh.txt").write_text("我是一名有5年经验的软件工程师。", encoding="utf-8")
    (prompts_dir / "Resume_format_prompts_zh.txt").write_text(
        "\\documentclass{article}\\usepackage{xeCJK}", encoding="utf-8"
    )
    (prompts_dir / "Application_question_prompt_zh.txt").write_text(
        "回答: {{USER_INFORMATION}} 职位: {{JOB_DESCRIPTION}} 问题: {{QUESTION}} 字数: {{WORD_LIMIT}}",
        encoding="utf-8",
    )
    (prompts_dir / "Application_question_prompt_no_fabrication_zh.txt").write_text(
        "回答禁止虚构: {{USER_INFORMATION}} 职位: {{JOB_DESCRIPTION}} 问题: {{QUESTION}} 字数: {{WORD_LIMIT}} 仅真实信息。",
        encoding="utf-8",
    )
    return prompts_dir


@pytest.fixture
def prompt_manager(tmp_prompts_dir):
    """A PromptManager instance pointing at temp files."""
    from services.prompt_manager import PromptManager

    return PromptManager(prompts_dir=tmp_prompts_dir)


@pytest.fixture
def task_manager_isolated(tmp_path, prompt_manager):
    """
    A TaskManager with mocked services so no real I/O occurs.
    Uses a temp data dir and mocked Gemini client.
    """
    from services.task_manager import TaskManager

    # Reset singleton so we get a fresh instance
    TaskManager._instance = None

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with (
        patch("services.task_manager.TASKS_FILE", data_dir / "tasks.json"),
        patch("services.task_manager.JD_HISTORY_FILE", data_dir / "jd_history.json"),
        patch("services.task_manager.settings") as mock_settings,
    ):
        mock_settings.data_dir = data_dir
        mock_settings.output_dir = tmp_path / "output"
        mock_settings.output_dir.mkdir()
        mock_settings.max_concurrent_tasks = 3
        mock_settings.max_latex_retries = 3

        tm = TaskManager.__new__(TaskManager)
        tm._initialized = False
        TaskManager._instance = tm

        # Manually initialize to avoid loading real config
        tm._initialized = True
        tm.tasks = {}
        tm.task_counter = 0
        tm._progress_callbacks = []
        tm._semaphore = asyncio.Semaphore(3)
        tm._lock = asyncio.Lock()
        tm.gemini_client = MagicMock()
        tm.settings_manager = MagicMock()
        tm.prompt_manager = prompt_manager
        tm.pdf_extractor = MagicMock()
        tm.text_to_pdf = MagicMock()

        # Make settings_manager.get return sensible defaults
        tm.settings_manager.get.return_value = True

        # Override _save_tasks to write to temp path (async version)
        tasks_file = data_dir / "tasks.json"

        async def patched_save():
            data = {
                "task_counter": tm.task_counter,
                "tasks": [t.model_dump(mode="json") for t in tm.tasks.values()],
            }
            tasks_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        tm._save_tasks = patched_save

        yield tm

        # Reset singleton
        TaskManager._instance = None


@pytest.fixture
def settings_manager_isolated(tmp_path):
    """SettingsManager backed by a temp file so tests never touch real settings."""
    from services.settings_manager import SettingsManager

    return SettingsManager(settings_file=tmp_path / "settings.json")


@pytest.fixture
def mock_ai_provider():
    """An AsyncMock AI provider returning canned LaTeX/text."""
    provider = AsyncMock()
    provider.provider_name = "mock"
    provider.model = "mock-model-1"
    provider.generate = AsyncMock(
        return_value=(
            "% META_COMPANY: TestCo\n"
            "% META_POSITION: Engineer\n"
            "\\documentclass[letterpaper,10pt]{article}\n"
            "\\begin{document}\n"
            "Hello World\n"
            "\\end{document}"
        )
    )
    provider.generate_resume = AsyncMock(
        return_value=("\\documentclass[letterpaper,10pt]{article}\n\\begin{document}\nResume content\n\\end{document}")
    )
    provider.generate_cover_letter = AsyncMock(return_value="Dear Hiring Manager,\n\nI am writing...")
    provider.generate_resume_with_error_feedback = AsyncMock(
        return_value=("\\documentclass[letterpaper,10pt]{article}\n\\begin{document}\nFixed resume\n\\end{document}")
    )
    return provider


@pytest.fixture
def sample_resume_state():
    """Pre-populated ResumeState dict for agent tests."""
    return {
        "task_id": "test-123",
        "task_number": 1,
        "job_description": "We are looking for a software engineer with Python experience.",
        "language": "en",
        "template_id": "classic",
        "generate_cover_letter": True,
        "provider_name": "gemini",
        "user_information": "I am a software engineer with 5 years of experience in Python.",
        "jd_analysis": {
            "job_title": "Software Engineer",
            "company_name": "TestCo",
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["Docker", "AWS"],
            "experience_level": "3-5 years",
            "key_responsibilities": ["Build APIs", "Write tests"],
            "industry": "Technology",
        },
        "relevance_match": {
            "matched_skills": ["Python", "FastAPI"],
            "missing_skills": ["Docker"],
            "relevant_experiences": ["Built REST APIs"],
            "emphasis_points": ["Python expertise", "API development"],
            "match_score": 0.8,
        },
        "retry_count": 0,
        "agent_outputs": {},
    }


@pytest.fixture
def valid_latex_source():
    """A valid LaTeX document string."""
    return (
        "\\documentclass[letterpaper,10pt]{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\begin{document}\n"
        "\\section{Experience}\n"
        "Software Engineer at TestCo.\n"
        "\\end{document}"
    )
