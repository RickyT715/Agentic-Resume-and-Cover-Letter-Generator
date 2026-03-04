"""
Prompt Manager Service
Handles loading, saving, and template substitution for prompts.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompt templates with file persistence and template substitution."""

    PROMPT_FILES = {
        "resume_prompt": "Resume_prompts.txt",
        "resume_prompt_no_fabrication": "Resume_prompts_no_fabrication.txt",
        "cover_letter_prompt": "Cover_letter_prompt.txt",
        "cover_letter_prompt_no_fabrication": "Cover_letter_prompt_no_fabrication.txt",
        "user_information": "User_information_prompts.txt",
        "resume_format": "Resume_format_prompts.txt",
        "resume_format_no_summary": "Resume_format_no_summary.txt",
        "application_question_prompt": "Application_question_prompt.txt",
        "application_question_prompt_no_fabrication": "Application_question_prompt_no_fabrication.txt",
        "resume_prompt_zh": "Resume_prompts_zh.txt",
        "resume_prompt_no_fabrication_zh": "Resume_prompts_no_fabrication_zh.txt",
        "cover_letter_prompt_zh": "Cover_letter_prompt_zh.txt",
        "cover_letter_prompt_no_fabrication_zh": "Cover_letter_prompt_no_fabrication_zh.txt",
        "user_information_zh": "User_information_prompts_zh.txt",
        "resume_format_zh": "Resume_format_prompts_zh.txt",
        "resume_format_no_summary_zh": "Resume_format_no_summary_zh.txt",
        "application_question_prompt_zh": "Application_question_prompt_zh.txt",
        "application_question_prompt_no_fabrication_zh": "Application_question_prompt_no_fabrication_zh.txt",
    }

    def __init__(self, prompts_dir: Path | None = None):
        """
        Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing prompt files
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent.parent / "prompts"

        self.prompts_dir = prompts_dir
        self._cache: dict[str, str] = {}
        self._load_all_prompts()

    def _load_all_prompts(self) -> None:
        """Load all prompts from files into cache."""
        for prompt_key, filename in self.PROMPT_FILES.items():
            filepath = self.prompts_dir / filename
            if filepath.exists():
                try:
                    self._cache[prompt_key] = filepath.read_text(encoding="utf-8")
                    logger.info(f"Loaded prompt: {prompt_key} from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load prompt {prompt_key}: {e}")
                    self._cache[prompt_key] = ""
            else:
                logger.warning(f"Prompt file not found: {filepath}")
                self._cache[prompt_key] = ""

    def get_prompt(self, prompt_key: str) -> str:
        """
        Get a prompt by key.

        Args:
            prompt_key: Key of the prompt (resume_prompt, cover_letter_prompt, etc.)

        Returns:
            Prompt content
        """
        return self._cache.get(prompt_key, "")

    def get_all_prompts(self) -> dict[str, str]:
        """Get all prompts as a dictionary."""
        return self._cache.copy()

    def update_prompt(self, prompt_key: str, content: str) -> bool:
        """
        Update a prompt and save to file.

        Args:
            prompt_key: Key of the prompt to update
            content: New content

        Returns:
            True if successful, False otherwise
        """
        if prompt_key not in self.PROMPT_FILES:
            logger.error(f"Invalid prompt key: {prompt_key}")
            return False

        filename = self.PROMPT_FILES[prompt_key]
        filepath = self.prompts_dir / filename

        try:
            filepath.write_text(content, encoding="utf-8")
            self._cache[prompt_key] = content
            logger.info(f"Updated prompt: {prompt_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save prompt {prompt_key}: {e}")
            return False

    def get_resume_prompt_with_substitutions(
        self,
        job_description: str,
        template_id: str = "classic",
        language: str = "en",
        experience_level: str = "auto",
        enforce_one_page: bool = False,
        allow_fabrication: bool = True,
    ) -> str:
        """
        Get the resume prompt with all template substitutions applied.

        Substitutes:
        - {{user_information}} -> content from User_information_prompts.txt
        - {{latex_template}} -> content from Resume_format_prompts.txt
        - {{JOB_DESCRIPTION}} -> provided job description

        Args:
            job_description: The job description to insert
            template_id: The resume template style to use
            language: Language code ("en" or "zh")
            experience_level: "auto", "new_grad", or "experienced"

        Returns:
            Fully substituted prompt
        """
        suffix = "_zh" if language == "zh" else ""

        # Select prompt variant based on fabrication setting
        if allow_fabrication:
            prompt = self.get_prompt(f"resume_prompt{suffix}")
        else:
            prompt = self.get_prompt(f"resume_prompt_no_fabrication{suffix}")

        user_info = self.get_prompt(f"user_information{suffix}")

        # Select format variant: no-summary template when one-page is enforced
        if enforce_one_page:
            latex_template = self.get_prompt(f"resume_format_no_summary{suffix}")
        else:
            latex_template = self.get_prompt(f"resume_format{suffix}")

        # Perform substitutions
        prompt = prompt.replace("{{user_information}}", user_info)
        prompt = prompt.replace("{{latex_template}}", latex_template)
        prompt = prompt.replace("{{JOB_DESCRIPTION}}", job_description)

        # Append template style instructions if not classic
        if template_id and template_id != "classic":
            template_instructions = self._load_template_instructions(template_id)
            if template_instructions:
                prompt += f"\n\n## Resume Style Instructions\n{template_instructions}"

        # Append experience level override if explicitly set
        if experience_level and experience_level != "auto":
            if language == "zh":
                override = self._get_experience_level_override_zh(
                    experience_level, enforce_one_page
                )
            else:
                override = self._get_experience_level_override(
                    experience_level, enforce_one_page
                )
            prompt += f"\n\n{override}"

        # Append no-summary override when one-page format is enforced.
        # This must come AFTER all other instructions so it takes precedence
        # over any Summary-related instructions in the prompt text.
        if enforce_one_page:
            if language == "zh":
                prompt += f"\n\n{self._get_no_summary_override_zh()}"
            else:
                prompt += f"\n\n{self._get_no_summary_override()}"

        logger.debug(
            f"Applied template substitutions (template={template_id}, experience={experience_level}, "
            f"fabrication={allow_fabrication}, one_page={enforce_one_page}) to resume prompt"
        )
        return prompt

    def _get_experience_level_override(
        self, level: str, enforce_one_page: bool = False
    ) -> str:
        """Get English experience level override instructions."""
        if level == "new_grad":
            return (
                "## Experience Level: New Graduate\n"
                "The candidate is a new graduate. Follow this layout STRICTLY:\n"
                "- Section order: Education → Technical Skills → Experience (internships) → Projects\n"
                "- Do NOT include a Summary/Objective section\n"
                "- Emphasize education (GPA, relevant coursework, honors) and projects over work experience\n"
                "- List internships under Experience but keep them concise (2-3 bullets each)"
            )
        else:  # experienced
            if enforce_one_page:
                return (
                    "## Experience Level: Experienced Professional\n"
                    "The candidate is an experienced professional. Follow this layout STRICTLY:\n"
                    "- Section order: Experience → Projects → Technical Skills → Education\n"
                    "- Do NOT include a Summary section — go directly to Experience after contact info\n"
                    "- Emphasize work experience with detailed bullets (3-5 per role)\n"
                    "- Education section should be minimal (degree, university, date only)"
                )
            return (
                "## Experience Level: Experienced Professional\n"
                "The candidate is an experienced professional. Follow this layout STRICTLY:\n"
                "- Section order: Summary → Experience → Projects → Technical Skills → Education\n"
                "- MUST include a Summary section (1-2 sentences with years of experience, core domain, key technologies)\n"
                "- Emphasize work experience with detailed bullets (3-5 per role)\n"
                "- Education section should be minimal (degree, university, date only)"
            )

    def _get_experience_level_override_zh(
        self, level: str, enforce_one_page: bool = False
    ) -> str:
        """Get Chinese experience level override instructions."""
        if level == "new_grad":
            return (
                "## 经验等级：应届毕业生\n"
                "候选人是应届毕业生。请严格按照以下布局：\n"
                "- 板块顺序：教育背景 → 技术技能 → 工作经验（实习） → 项目经历\n"
                "- 不要包含个人总结部分\n"
                "- 重点突出教育背景（GPA、相关课程、荣誉）和项目经历\n"
                "- 实习经历放在工作经验下，每段保持简洁（2-3个要点）"
            )
        else:  # experienced
            if enforce_one_page:
                return (
                    "## 经验等级：有经验的专业人士\n"
                    "候选人是有经验的专业人士。请严格按照以下布局：\n"
                    "- 板块顺序：工作经验 → 项目经历 → 技术技能 → 教育背景\n"
                    "- 不要包含个人总结——联系方式之后直接开始工作经验\n"
                    "- 重点突出工作经验，每段3-5个详细要点\n"
                    "- 教育背景保持简洁（学位、学校、日期即可）"
                )
            return (
                "## 经验等级：有经验的专业人士\n"
                "候选人是有经验的专业人士。请严格按照以下布局：\n"
                "- 板块顺序：个人总结 → 工作经验 → 项目经历 → 技术技能 → 教育背景\n"
                "- 必须包含个人总结（1-2句，包含工作年限、核心领域、关键技术）\n"
                "- 重点突出工作经验，每段3-5个详细要点\n"
                "- 教育背景保持简洁（学位、学校、日期即可）"
            )

    def _get_no_summary_override(self) -> str:
        """Get English no-summary override for one-page enforcement."""
        return (
            "## CRITICAL OVERRIDE: No Summary Section (One-Page Format)\n"
            "The one-page format is enforced. The provided LaTeX template does NOT "
            "contain a Summary section.\n"
            "You MUST follow these rules — they OVERRIDE any earlier instructions:\n"
            "- Do NOT include a Summary or Objective section anywhere in the resume\n"
            "- Do NOT add a \\section{Summary} command — it is not in the template\n"
            "- Begin resume content with Experience or Technical Skills immediately "
            "after the contact header\n"
            "- Ignore any earlier instructions about including a Summary section, "
            "Summary in the quality checklist, or Summary in keyword distribution\n"
            "- Distribute keywords across Experience bullets and Skills section instead"
        )

    def _get_no_summary_override_zh(self) -> str:
        """Get Chinese no-summary override for one-page enforcement."""
        return (
            "## 重要覆盖：不包含个人总结（单页格式）\n"
            "已启用单页格式。提供的LaTeX模板中不包含「个人总结」板块。\n"
            "你必须遵循以下规则——它们覆盖上述所有相关指令：\n"
            "- 不要在简历任何位置包含「个人总结」或「求职目标」板块\n"
            "- 不要添加 \\section{个人总结} 命令——模板中没有此板块\n"
            "- 简历内容从联系方式后直接开始「工作经验」或「技术技能」板块\n"
            "- 忽略上述约束和质量检查表中关于个人总结的任何指令\n"
            "- 将关键词分布在工作经验要点和技能部分中，而不是个人总结"
        )

    def _load_template_instructions(self, template_id: str) -> str:
        """Load template style instructions from the templates directory."""
        from config import settings

        template_file = settings.templates_dir / f"{template_id}.txt"
        if template_file.exists():
            try:
                return template_file.read_text(encoding="utf-8").strip()
            except Exception as e:
                logger.error(f"Failed to load template {template_id}: {e}")
        return ""

    def get_cover_letter_prompt_with_substitutions(
        self,
        resume_content: str,
        job_description: str,
        language: str = "en",
        allow_fabrication: bool = True,
    ) -> str:
        """
        Get the cover letter prompt with all template substitutions applied.

        Substitutes:
        - {{RESUME_CONTENT}} -> provided resume content
        - {{JOB_DESCRIPTION}} -> provided job description

        Args:
            resume_content: The resume content to insert
            job_description: The job description to insert
            language: Language code ("en" or "zh")

        Returns:
            Fully substituted prompt
        """
        suffix = "_zh" if language == "zh" else ""

        # Select prompt variant based on fabrication setting
        if allow_fabrication:
            prompt = self.get_prompt(f"cover_letter_prompt{suffix}")
        else:
            prompt = self.get_prompt(f"cover_letter_prompt_no_fabrication{suffix}")

        # Perform substitutions
        prompt = prompt.replace("{{RESUME_CONTENT}}", resume_content)
        prompt = prompt.replace("{{JOB_DESCRIPTION}}", job_description)

        logger.debug("Applied template substitutions to cover letter prompt")
        return prompt

    def get_question_prompt_with_substitutions(
        self,
        question: str,
        job_description: str,
        word_limit: int = 150,
        language: str = "en",
        allow_fabrication: bool = True,
    ) -> str:
        """
        Get the application question prompt with all template substitutions applied.

        Substitutes:
        - {{USER_INFORMATION}} -> content from User_information_prompts.txt
        - {{JOB_DESCRIPTION}} -> provided job description
        - {{QUESTION}} -> the application question
        - {{WORD_LIMIT}} -> the word limit

        Args:
            question: The application question to answer
            job_description: The job description for context
            word_limit: Maximum word count for the answer
            language: Language code ("en" or "zh")

        Returns:
            Fully substituted prompt
        """
        suffix = "_zh" if language == "zh" else ""

        # Select prompt variant based on fabrication setting
        if allow_fabrication:
            prompt = self.get_prompt(f"application_question_prompt{suffix}")
        else:
            prompt = self.get_prompt(f"application_question_prompt_no_fabrication{suffix}")

        user_info = self.get_prompt(f"user_information{suffix}")

        prompt = prompt.replace("{{USER_INFORMATION}}", user_info)
        prompt = prompt.replace("{{JOB_DESCRIPTION}}", job_description)
        prompt = prompt.replace("{{QUESTION}}", question)
        prompt = prompt.replace("{{WORD_LIMIT}}", str(word_limit))

        logger.debug("Applied template substitutions to application question prompt")
        return prompt

    def validate_prompt(self, prompt_key: str, content: str) -> list:
        """
        Validate a prompt for required placeholders.
        Returns a list of warning messages (empty = no issues).
        """
        warnings = []
        # Strip _zh and _no_fabrication suffixes to apply same validation rules
        base_key = prompt_key.removesuffix("_zh").removesuffix("_no_fabrication")
        if base_key == "resume_prompt":
            for placeholder in ["{{user_information}}", "{{latex_template}}", "{{JOB_DESCRIPTION}}"]:
                if placeholder not in content:
                    warnings.append(f"Missing required placeholder: {placeholder}")
        elif base_key == "cover_letter_prompt":
            for placeholder in ["{{RESUME_CONTENT}}", "{{JOB_DESCRIPTION}}"]:
                if placeholder not in content:
                    warnings.append(f"Missing required placeholder: {placeholder}")
        elif base_key == "application_question_prompt":
            for placeholder in ["{{USER_INFORMATION}}", "{{JOB_DESCRIPTION}}", "{{QUESTION}}", "{{WORD_LIMIT}}"]:
                if placeholder not in content:
                    warnings.append(f"Missing required placeholder: {placeholder}")
        return warnings

    def reload_prompts(self) -> None:
        """Reload all prompts from files."""
        self._cache.clear()
        self._load_all_prompts()
        logger.info("Reloaded all prompts")


# Global prompt manager instance
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
