"""Tests for PromptManager prompt support including Chinese language."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestQuestionPromptRegistered:
    def test_prompt_file_registered(self, prompt_manager):
        assert "application_question_prompt" in prompt_manager.PROMPT_FILES
        assert prompt_manager.PROMPT_FILES["application_question_prompt"] == "Application_question_prompt.txt"

    def test_prompt_loaded(self, prompt_manager):
        content = prompt_manager.get_prompt("application_question_prompt")
        assert content != ""
        assert "{{USER_INFORMATION}}" in content or "USER_INFORMATION" in content


class TestQuestionPromptSubstitution:
    def test_all_placeholders_substituted(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Why do you want to work here?",
            job_description="Software Engineer at Acme Corp",
            word_limit=200,
        )
        assert "{{USER_INFORMATION}}" not in result
        assert "{{JOB_DESCRIPTION}}" not in result
        assert "{{QUESTION}}" not in result
        assert "{{WORD_LIMIT}}" not in result

    def test_user_information_injected(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Q", job_description="JD", word_limit=150
        )
        assert "software engineer with 5 years" in result

    def test_job_description_injected(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Q", job_description="Machine Learning Engineer at Google"
        )
        assert "Machine Learning Engineer at Google" in result

    def test_question_injected(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Describe a challenge you overcame",
            job_description="JD",
        )
        assert "Describe a challenge you overcame" in result

    def test_word_limit_injected(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Q", job_description="JD", word_limit=300
        )
        assert "300" in result

    def test_default_word_limit(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Q", job_description="JD"
        )
        assert "150" in result


class TestQuestionPromptValidation:
    def test_valid_prompt_no_warnings(self, prompt_manager):
        content = "{{USER_INFORMATION}} {{JOB_DESCRIPTION}} {{QUESTION}} {{WORD_LIMIT}}"
        warnings = prompt_manager.validate_prompt("application_question_prompt", content)
        assert warnings == []

    def test_missing_placeholder_warns(self, prompt_manager):
        content = "{{USER_INFORMATION}} {{JOB_DESCRIPTION}}"
        warnings = prompt_manager.validate_prompt("application_question_prompt", content)
        assert len(warnings) == 2
        assert any("{{QUESTION}}" in w for w in warnings)
        assert any("{{WORD_LIMIT}}" in w for w in warnings)

    def test_all_placeholders_missing(self, prompt_manager):
        warnings = prompt_manager.validate_prompt("application_question_prompt", "no placeholders")
        assert len(warnings) == 4


class TestChinesePromptRegistered:
    def test_zh_prompt_files_registered(self, prompt_manager):
        for key in ["resume_prompt_zh", "cover_letter_prompt_zh", "user_information_zh",
                     "resume_format_zh", "application_question_prompt_zh"]:
            assert key in prompt_manager.PROMPT_FILES

    def test_zh_prompts_loaded(self, prompt_manager):
        assert prompt_manager.get_prompt("resume_prompt_zh") != ""
        assert prompt_manager.get_prompt("cover_letter_prompt_zh") != ""
        assert prompt_manager.get_prompt("application_question_prompt_zh") != ""


class TestChineseResumePromptSubstitution:
    def test_zh_resume_prompt_substitution(self, prompt_manager):
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="软件工程师", template_id="classic", language="zh"
        )
        assert "{{user_information}}" not in result
        assert "{{latex_template}}" not in result
        assert "{{JOB_DESCRIPTION}}" not in result
        assert "软件工程师" in result
        assert "5年经验" in result

    def test_en_resume_prompt_unaffected(self, prompt_manager):
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE", language="en"
        )
        assert "software engineer with 5 years" in result


class TestChineseCoverLetterSubstitution:
    def test_zh_cover_letter_substitution(self, prompt_manager):
        result = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="我的简历", job_description="AI工程师", language="zh"
        )
        assert "{{RESUME_CONTENT}}" not in result
        assert "{{JOB_DESCRIPTION}}" not in result
        assert "我的简历" in result
        assert "AI工程师" in result


class TestChineseQuestionPromptSubstitution:
    def test_zh_question_prompt_substitution(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="你为什么想加入我们？",
            job_description="后端开发",
            word_limit=200,
            language="zh",
        )
        assert "{{USER_INFORMATION}}" not in result
        assert "{{JOB_DESCRIPTION}}" not in result
        assert "{{QUESTION}}" not in result
        assert "{{WORD_LIMIT}}" not in result
        assert "你为什么想加入我们？" in result
        assert "5年经验" in result


class TestChinesePromptValidation:
    def test_zh_resume_prompt_validation(self, prompt_manager):
        content = "{{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}"
        warnings = prompt_manager.validate_prompt("resume_prompt_zh", content)
        assert warnings == []

    def test_zh_resume_prompt_missing_placeholder(self, prompt_manager):
        warnings = prompt_manager.validate_prompt("resume_prompt_zh", "no placeholders")
        assert len(warnings) == 3

    def test_zh_question_prompt_validation(self, prompt_manager):
        content = "{{USER_INFORMATION}} {{JOB_DESCRIPTION}} {{QUESTION}} {{WORD_LIMIT}}"
        warnings = prompt_manager.validate_prompt("application_question_prompt_zh", content)
        assert warnings == []


class TestTaskLanguageBackwardCompat:
    def test_task_default_language(self):
        from models.task import Task
        task = Task(task_number=1, job_description="test")
        assert task.language == "en"

    def test_task_create_default_language(self):
        from models.task import TaskCreate
        tc = TaskCreate()
        assert tc.language == "en"

    def test_task_with_zh_language(self):
        from models.task import Task
        task = Task(task_number=1, job_description="test", language="zh")
        assert task.language == "zh"

    def test_task_from_dict_without_language(self):
        from models.task import Task
        data = {"task_number": 1, "job_description": "test"}
        task = Task(**data)
        assert task.language == "en"
