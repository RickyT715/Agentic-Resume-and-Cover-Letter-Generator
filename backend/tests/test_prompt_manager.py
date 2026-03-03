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
        result = prompt_manager.get_question_prompt_with_substitutions(question="Q", job_description="JD")
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
        for key in [
            "resume_prompt_zh",
            "cover_letter_prompt_zh",
            "user_information_zh",
            "resume_format_zh",
            "application_question_prompt_zh",
        ]:
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
        result = prompt_manager.get_resume_prompt_with_substitutions(job_description="SWE", language="en")
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


class TestNoFabricationPromptRegistered:
    """Tests that no-fabrication prompt variants are registered and loaded."""

    def test_no_fabrication_prompt_files_registered(self, prompt_manager):
        for key in [
            "resume_prompt_no_fabrication",
            "cover_letter_prompt_no_fabrication",
            "application_question_prompt_no_fabrication",
            "resume_prompt_no_fabrication_zh",
            "cover_letter_prompt_no_fabrication_zh",
            "application_question_prompt_no_fabrication_zh",
        ]:
            assert key in prompt_manager.PROMPT_FILES, f"Missing key: {key}"

    def test_no_fabrication_prompts_loaded(self, prompt_manager):
        assert prompt_manager.get_prompt("resume_prompt_no_fabrication") != ""
        assert prompt_manager.get_prompt("cover_letter_prompt_no_fabrication") != ""
        assert prompt_manager.get_prompt("application_question_prompt_no_fabrication") != ""

    def test_no_fabrication_zh_prompts_loaded(self, prompt_manager):
        assert prompt_manager.get_prompt("resume_prompt_no_fabrication_zh") != ""
        assert prompt_manager.get_prompt("cover_letter_prompt_no_fabrication_zh") != ""
        assert prompt_manager.get_prompt("application_question_prompt_no_fabrication_zh") != ""


class TestNoSummaryFormatRegistered:
    """Tests that no-summary format templates are registered and loaded."""

    def test_no_summary_format_files_registered(self, prompt_manager):
        assert "resume_format_no_summary" in prompt_manager.PROMPT_FILES
        assert "resume_format_no_summary_zh" in prompt_manager.PROMPT_FILES

    def test_no_summary_format_loaded(self, prompt_manager):
        content = prompt_manager.get_prompt("resume_format_no_summary")
        assert content != ""
        assert "No Summary" in content or "Education" in content

    def test_no_summary_format_zh_loaded(self, prompt_manager):
        content = prompt_manager.get_prompt("resume_format_no_summary_zh")
        assert content != ""
        assert "无个人总结" in content or "教育背景" in content


class TestResumePromptFabricationVariantSelection:
    """Tests that resume prompt correctly selects fabrication vs no-fabrication variants."""

    def test_default_uses_fabrication_variant(self, prompt_manager):
        """allow_fabrication=True (default) should use the standard resume prompt."""
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE at Google", allow_fabrication=True
        )
        assert "Resume prompt" in result or "{{user_information}}" not in result
        # Should NOT contain no-fabrication marker
        assert "no-fabrication" not in result.lower() or "Only use verified" not in result

    def test_no_fabrication_uses_different_prompt(self, prompt_manager):
        """allow_fabrication=False should use the no-fabrication resume prompt."""
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE at Google", allow_fabrication=False
        )
        assert "no-fabrication" in result.lower() or "Only use verified" in result

    def test_fabrication_and_no_fabrication_are_different(self, prompt_manager):
        """The two variants should produce different outputs."""
        with_fab = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE at Google", allow_fabrication=True
        )
        without_fab = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE at Google", allow_fabrication=False
        )
        assert with_fab != without_fab

    def test_no_fabrication_zh_variant(self, prompt_manager):
        """Chinese no-fabrication variant should be selected."""
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="软件工程师", language="zh", allow_fabrication=False
        )
        assert "禁止虚构" in result or "仅使用真实" in result

    def test_all_placeholders_substituted_in_no_fab(self, prompt_manager):
        """No-fabrication variant should still perform all substitutions."""
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="ML Engineer", allow_fabrication=False
        )
        assert "{{user_information}}" not in result
        assert "{{latex_template}}" not in result
        assert "{{JOB_DESCRIPTION}}" not in result
        assert "ML Engineer" in result


class TestCoverLetterFabricationVariantSelection:
    """Tests that cover letter prompt correctly selects variants."""

    def test_default_uses_fabrication_variant(self, prompt_manager):
        result = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="My resume", job_description="SWE", allow_fabrication=True
        )
        assert "no-fabrication" not in result.lower() or "No invented" not in result

    def test_no_fabrication_uses_different_prompt(self, prompt_manager):
        result = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="My resume", job_description="SWE", allow_fabrication=False
        )
        assert "no-fabrication" in result.lower() or "No invented" in result

    def test_fabrication_and_no_fabrication_are_different(self, prompt_manager):
        with_fab = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="My resume", job_description="SWE", allow_fabrication=True
        )
        without_fab = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="My resume", job_description="SWE", allow_fabrication=False
        )
        assert with_fab != without_fab

    def test_no_fabrication_zh_variant(self, prompt_manager):
        result = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="我的简历", job_description="AI工程师", language="zh", allow_fabrication=False
        )
        assert "禁止虚构" in result or "不编造" in result

    def test_all_placeholders_substituted_in_no_fab(self, prompt_manager):
        result = prompt_manager.get_cover_letter_prompt_with_substitutions(
            resume_content="My resume content", job_description="Data Scientist", allow_fabrication=False
        )
        assert "{{RESUME_CONTENT}}" not in result
        assert "{{JOB_DESCRIPTION}}" not in result
        assert "My resume content" in result
        assert "Data Scientist" in result


class TestQuestionFabricationVariantSelection:
    """Tests that application question prompt correctly selects variants."""

    def test_default_uses_fabrication_variant(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Tell me about yourself", job_description="SWE", allow_fabrication=True
        )
        assert "no-fabrication" not in result.lower() or "Only real facts" not in result

    def test_no_fabrication_uses_different_prompt(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Tell me about yourself", job_description="SWE", allow_fabrication=False
        )
        assert "no-fabrication" in result.lower() or "Only real facts" in result

    def test_fabrication_and_no_fabrication_are_different(self, prompt_manager):
        with_fab = prompt_manager.get_question_prompt_with_substitutions(
            question="Q", job_description="JD", allow_fabrication=True
        )
        without_fab = prompt_manager.get_question_prompt_with_substitutions(
            question="Q", job_description="JD", allow_fabrication=False
        )
        assert with_fab != without_fab

    def test_no_fabrication_zh_variant(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="你为什么想加入我们？", job_description="后端开发", language="zh", allow_fabrication=False
        )
        assert "禁止虚构" in result or "仅真实" in result

    def test_all_placeholders_substituted_in_no_fab(self, prompt_manager):
        result = prompt_manager.get_question_prompt_with_substitutions(
            question="Why this company?", job_description="PM role", word_limit=250, allow_fabrication=False
        )
        assert "{{USER_INFORMATION}}" not in result
        assert "{{JOB_DESCRIPTION}}" not in result
        assert "{{QUESTION}}" not in result
        assert "{{WORD_LIMIT}}" not in result
        assert "Why this company?" in result
        assert "250" in result


class TestOnePageFormatSelection:
    """Tests that enforce_one_page selects the no-summary template."""

    def test_default_uses_standard_format(self, prompt_manager):
        """enforce_one_page=False should use standard resume_format."""
        result = prompt_manager.get_resume_prompt_with_substitutions(job_description="SWE", enforce_one_page=False)
        # Standard format should NOT have "No Summary" marker
        assert "No Summary" not in result or "无个人总结" not in result

    def test_one_page_uses_no_summary_format(self, prompt_manager):
        """enforce_one_page=True should use resume_format_no_summary."""
        result = prompt_manager.get_resume_prompt_with_substitutions(job_description="SWE", enforce_one_page=True)
        assert "No Summary" in result or "Education" in result

    def test_one_page_zh_uses_no_summary_format(self, prompt_manager):
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="软件工程师", language="zh", enforce_one_page=True
        )
        assert "无个人总结" in result or "教育背景" in result

    def test_standard_and_one_page_formats_are_different(self, prompt_manager):
        standard = prompt_manager.get_resume_prompt_with_substitutions(job_description="SWE", enforce_one_page=False)
        one_page = prompt_manager.get_resume_prompt_with_substitutions(job_description="SWE", enforce_one_page=True)
        assert standard != one_page


class TestCombinedFabricationAndOnePage:
    """Tests that no-fabrication + one-page can be combined correctly."""

    def test_no_fab_plus_one_page(self, prompt_manager):
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="SWE", allow_fabrication=False, enforce_one_page=True
        )
        # Should use no-fabrication prompt
        assert "no-fabrication" in result.lower() or "Only use verified" in result
        # Should use no-summary template
        assert "No Summary" in result or "Education" in result

    def test_no_fab_plus_one_page_zh(self, prompt_manager):
        result = prompt_manager.get_resume_prompt_with_substitutions(
            job_description="软件工程师", language="zh", allow_fabrication=False, enforce_one_page=True
        )
        assert "禁止虚构" in result or "仅使用真实" in result
        assert "无个人总结" in result or "教育背景" in result

    def test_all_four_combinations_are_unique(self, prompt_manager):
        """All 4 combinations of fabrication x one_page should produce unique results."""
        results = set()
        for fab in [True, False]:
            for one_page in [True, False]:
                result = prompt_manager.get_resume_prompt_with_substitutions(
                    job_description="SWE", allow_fabrication=fab, enforce_one_page=one_page
                )
                results.add(result)
        assert len(results) == 4


class TestNoFabricationPromptValidation:
    """Tests that validate_prompt works for no-fabrication variants."""

    def test_valid_no_fab_resume_prompt(self, prompt_manager):
        content = "{{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}"
        warnings = prompt_manager.validate_prompt("resume_prompt_no_fabrication", content)
        assert warnings == []

    def test_valid_no_fab_resume_prompt_zh(self, prompt_manager):
        content = "{{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}"
        warnings = prompt_manager.validate_prompt("resume_prompt_no_fabrication_zh", content)
        assert warnings == []

    def test_missing_placeholder_in_no_fab_resume(self, prompt_manager):
        content = "No placeholders here"
        warnings = prompt_manager.validate_prompt("resume_prompt_no_fabrication", content)
        assert len(warnings) == 3

    def test_valid_no_fab_cover_letter(self, prompt_manager):
        content = "{{RESUME_CONTENT}} {{JOB_DESCRIPTION}}"
        warnings = prompt_manager.validate_prompt("cover_letter_prompt_no_fabrication", content)
        assert warnings == []

    def test_missing_placeholder_in_no_fab_cover_letter(self, prompt_manager):
        content = "{{RESUME_CONTENT}} only"
        warnings = prompt_manager.validate_prompt("cover_letter_prompt_no_fabrication", content)
        assert len(warnings) == 1
        assert any("{{JOB_DESCRIPTION}}" in w for w in warnings)

    def test_valid_no_fab_question_prompt(self, prompt_manager):
        content = "{{USER_INFORMATION}} {{JOB_DESCRIPTION}} {{QUESTION}} {{WORD_LIMIT}}"
        warnings = prompt_manager.validate_prompt("application_question_prompt_no_fabrication", content)
        assert warnings == []

    def test_missing_placeholder_in_no_fab_question(self, prompt_manager):
        content = "{{USER_INFORMATION}} {{JOB_DESCRIPTION}}"
        warnings = prompt_manager.validate_prompt("application_question_prompt_no_fabrication", content)
        assert len(warnings) == 2
        assert any("{{QUESTION}}" in w for w in warnings)
        assert any("{{WORD_LIMIT}}" in w for w in warnings)

    def test_no_fab_zh_question_prompt_validation(self, prompt_manager):
        content = "{{USER_INFORMATION}} {{JOB_DESCRIPTION}} {{QUESTION}} {{WORD_LIMIT}}"
        warnings = prompt_manager.validate_prompt("application_question_prompt_no_fabrication_zh", content)
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
