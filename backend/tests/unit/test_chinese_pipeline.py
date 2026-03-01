"""Tests for the complete Chinese language pipeline.

Covers:
- Chinese ATS scoring (action verbs, quantification, section detection)
- Chinese skill taxonomy (aliases, normalization)
- Chinese feedback generation
- Chinese quality gate heuristics
- Chinese agent prompt selection
- CJK text detection and font registration
- DeepSeek/Qwen provider creation
"""

import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

BACKEND_DIR = Path(__file__).parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Sample Chinese data ─────────────────────────────────────────────

SAMPLE_ZH_JD = """
职位名称：高级后端开发工程师
公司：字节跳动
工作职责：
- 负责后端服务架构设计与开发
- 优化系统性能，提升服务稳定性
- 参与微服务架构的搭建和治理
技术要求：
- 精通Python/Go/Java中的至少一种
- 熟悉微服务架构、Docker、Kubernetes
- 了解Redis、MySQL、Kafka等中间件
- 3-5年相关工作经验
"""

SAMPLE_ZH_RESUME_LATEX = r"""
\documentclass[a4paper,10pt]{article}
\usepackage{xeCJK}
\begin{document}

\section{工作经历}
\textbf{高级软件工程师} — 阿里巴巴 \hfill 2020--2024

\begin{itemize}
\item 主导设计了微服务架构迁移方案，将单体应用拆分为12个微服务，系统可用性从99.5\%提升至99.99\%
\item 架构并实现了基于Kafka的实时消息处理系统，日处理2000万条消息，延迟降低60\%
\item 优化MySQL慢查询，将P99响应时间从800ms缩短至120ms，提升85\%
\item 搭建CI/CD流水线，部署效率提升300\%
\end{itemize}

\section{教育背景}
\textbf{计算机科学与技术} — 清华大学 \hfill 2016--2020

\section{专业技能}
Python, Go, Java, Docker, Kubernetes, Redis, MySQL, Kafka, 微服务, FastAPI, gRPC

\section{项目经历}
\textbf{分布式任务调度平台}
\begin{itemize}
\item 设计并实现分布式任务调度系统，支持百万级定时任务
\item 引入Redis分布式锁，解决任务重复执行问题
\end{itemize}

\end{document}
"""

SAMPLE_ZH_JD_ANALYSIS = {
    "job_title": "高级后端开发工程师",
    "company_name": "字节跳动",
    "required_skills": ["Python", "Go", "微服务", "Docker", "Kubernetes"],
    "preferred_skills": ["Redis", "MySQL", "Kafka"],
    "experience_level": "3-5年",
    "key_responsibilities": ["后端服务架构设计", "系统性能优化", "微服务架构搭建"],
    "industry": "互联网",
}


# ═══════════════════════════════════════════════════════════════════════
# 1. Chinese Skill Taxonomy Tests
# ═══════════════════════════════════════════════════════════════════════


class TestChineseActionVerbs:
    def test_strong_verbs_exist(self):
        from evaluation.skills_taxonomy import ACTION_VERBS_ZH_STRONG

        assert len(ACTION_VERBS_ZH_STRONG) >= 20
        assert "主导" in ACTION_VERBS_ZH_STRONG
        assert "设计" in ACTION_VERBS_ZH_STRONG
        assert "架构" in ACTION_VERBS_ZH_STRONG
        assert "优化" in ACTION_VERBS_ZH_STRONG

    def test_medium_verbs_exist(self):
        from evaluation.skills_taxonomy import ACTION_VERBS_ZH_MEDIUM

        assert len(ACTION_VERBS_ZH_MEDIUM) >= 15
        assert "负责" in ACTION_VERBS_ZH_MEDIUM
        assert "开发" in ACTION_VERBS_ZH_MEDIUM

    def test_weak_verbs_exist(self):
        from evaluation.skills_taxonomy import ACTION_VERBS_ZH_WEAK

        assert len(ACTION_VERBS_ZH_WEAK) >= 5
        assert "参与" in ACTION_VERBS_ZH_WEAK
        assert "协助" in ACTION_VERBS_ZH_WEAK

    def test_no_overlap_between_tiers(self):
        from evaluation.skills_taxonomy import (
            ACTION_VERBS_ZH_MEDIUM,
            ACTION_VERBS_ZH_STRONG,
            ACTION_VERBS_ZH_WEAK,
        )

        assert not (ACTION_VERBS_ZH_STRONG & ACTION_VERBS_ZH_MEDIUM)
        assert not (ACTION_VERBS_ZH_STRONG & ACTION_VERBS_ZH_WEAK)
        assert not (ACTION_VERBS_ZH_MEDIUM & ACTION_VERBS_ZH_WEAK)

    def test_all_union(self):
        from evaluation.skills_taxonomy import (
            ACTION_VERBS_ZH_ALL,
            ACTION_VERBS_ZH_MEDIUM,
            ACTION_VERBS_ZH_STRONG,
            ACTION_VERBS_ZH_WEAK,
        )

        assert ACTION_VERBS_ZH_ALL == (
            ACTION_VERBS_ZH_STRONG | ACTION_VERBS_ZH_MEDIUM | ACTION_VERBS_ZH_WEAK
        )


class TestChineseSections:
    def test_expected_sections_keys(self):
        from evaluation.skills_taxonomy import EXPECTED_SECTIONS_ZH

        assert "教育" in EXPECTED_SECTIONS_ZH
        assert "工作" in EXPECTED_SECTIONS_ZH
        assert "项目" in EXPECTED_SECTIONS_ZH
        assert "技能" in EXPECTED_SECTIONS_ZH

    def test_section_variants(self):
        from evaluation.skills_taxonomy import EXPECTED_SECTIONS_ZH

        assert "教育背景" in EXPECTED_SECTIONS_ZH["教育"]
        assert "工作经历" in EXPECTED_SECTIONS_ZH["工作"]
        assert "专业技能" in EXPECTED_SECTIONS_ZH["技能"]

    def test_all_section_names_flat(self):
        from evaluation.skills_taxonomy import ALL_SECTION_NAMES_ZH

        assert "教育背景" in ALL_SECTION_NAMES_ZH
        assert "工作经历" in ALL_SECTION_NAMES_ZH
        assert "专业技能" in ALL_SECTION_NAMES_ZH
        assert "项目经历" in ALL_SECTION_NAMES_ZH


class TestChineseSkillAliases:
    def test_skill_aliases_structure(self):
        from evaluation.skills_taxonomy import SKILL_ALIASES_ZH

        assert len(SKILL_ALIASES_ZH) >= 50
        assert "机器学习" in SKILL_ALIASES_ZH
        assert "ML" in SKILL_ALIASES_ZH["机器学习"]

    def test_normalize_skill_zh(self):
        from evaluation.skills_taxonomy import normalize_skill_zh

        assert normalize_skill_zh("机器学习") == "机器学习"
        assert normalize_skill_zh("ML") == "机器学习"
        assert normalize_skill_zh("Machine Learning") == "机器学习"

    def test_normalize_skill_unknown(self):
        from evaluation.skills_taxonomy import normalize_skill_zh

        assert normalize_skill_zh("UnknownSkill123") == "UnknownSkill123"

    def test_bilingual_mappings(self):
        from evaluation.skills_taxonomy import normalize_skill_zh

        assert normalize_skill_zh("NLP") == "自然语言处理"
        assert normalize_skill_zh("Docker") == "容器化"
        assert normalize_skill_zh("Kubernetes") == "容器编排"
        assert normalize_skill_zh("微服务") == "微服务"


# ═══════════════════════════════════════════════════════════════════════
# 2. Chinese ATS Scorer Tests
# ═══════════════════════════════════════════════════════════════════════


class TestChineseATSScoring:
    def test_score_resume_with_language_zh(self):
        from evaluation.ats_scorer import score_resume

        result = score_resume(
            SAMPLE_ZH_RESUME_LATEX,
            SAMPLE_ZH_JD,
            SAMPLE_ZH_JD_ANALYSIS,
            language="zh",
        )
        assert result.overall > 0.0
        assert result.overall <= 1.0
        assert isinstance(result.matched_keywords, list)
        assert isinstance(result.missing_keywords, list)

    def test_auto_detect_chinese(self):
        from evaluation.ats_scorer import _is_chinese

        assert _is_chinese("这是一段中文文本，包含很多汉字")
        assert not _is_chinese("This is English text with no CJK chars")
        assert _is_chinese("Python开发工程师，3年经验")

    def test_chinese_quality_scoring(self):
        from evaluation.ats_scorer import _score_quality

        quality, verbs, quant, sections, fmt, feedback = _score_quality(
            "主导设计了微服务架构，优化系统性能提升30%，搭建CI/CD流水线",
            SAMPLE_ZH_RESUME_LATEX,
            language="zh",
        )
        assert quality > 0.0
        # Strong verbs should be detected
        assert verbs > 0.0
        # Quantified achievements should be detected
        assert quant > 0.0

    def test_chinese_quality_feedback_in_chinese(self):
        from evaluation.ats_scorer import _score_quality

        _, _, _, _, _, feedback = _score_quality(
            "参与了一些项目",
            r"\documentclass{article}\begin{document}参与了一些项目\end{document}",
            language="zh",
        )
        # Feedback should be in Chinese
        assert any("建议" in f or "动词" in f or "量化" in f for f in feedback)

    def test_english_quality_unchanged(self):
        from evaluation.ats_scorer import _score_quality

        _, _, _, _, _, feedback = _score_quality(
            "Led development of microservices, improved performance by 30%",
            r"\documentclass{article}\begin{document}Led development\end{document}",
            language="en",
        )
        # English feedback should be English
        assert not any("建议" in f for f in feedback)

    def test_chinese_missing_skills_feedback_in_chinese(self):
        from evaluation.ats_scorer import score_resume

        result = score_resume(
            r"\documentclass{article}\begin{document}简单简历\end{document}",
            SAMPLE_ZH_JD,
            SAMPLE_ZH_JD_ANALYSIS,
            language="zh",
        )
        # If there are missing keywords, feedback should be in Chinese
        if result.missing_keywords:
            zh_feedback = [f for f in result.feedback if "缺少" in f]
            assert len(zh_feedback) > 0


class TestChineseBM25:
    def test_bm25_chinese_tokenization(self):
        """BM25 should work with Chinese text via jieba."""
        from evaluation.ats_scorer import _score_bm25

        score = _score_bm25(
            "我有5年Python开发经验，熟悉微服务架构",
            "需要精通Python和微服务架构的高级工程师",
            language="zh",
        )
        assert 0.0 <= score <= 1.0

    def test_bm25_english_unchanged(self):
        from evaluation.ats_scorer import _score_bm25

        score = _score_bm25(
            "I have 5 years of Python development experience",
            "Looking for a senior Python developer",
            language="en",
        )
        assert 0.0 <= score <= 1.0


# ═══════════════════════════════════════════════════════════════════════
# 3. Chinese Feedback Generator Tests
# ═══════════════════════════════════════════════════════════════════════


class TestChineseFeedback:
    def test_generate_feedback_zh(self):
        from evaluation.ats_scorer import ATSScoreBreakdown
        from evaluation.feedback_generator import generate_feedback

        score = ATSScoreBreakdown(
            keyword_similarity=0.5,
            semantic_similarity=0.4,
            skill_coverage=0.3,
            fuzzy_match=0.6,
            resume_quality=0.5,
            section_bonus=0.4,
            action_verbs_score=0.3,
            quantified_score=0.2,
            section_score=0.5,
            format_score=0.6,
            overall=0.42,
            matched_keywords=["Python", "Go"],
            missing_keywords=["Docker", "Kubernetes"],
            feedback=["建议使用更多强动词"],
        )

        result = generate_feedback(score, None, 0.42, language="zh")

        assert "上一次生成得分" in result
        assert "ATS评估反馈" in result
        assert "缺失关键词" in result
        assert "各项评分" in result
        assert "关键词相关性" in result
        assert "请根据以上所有反馈重新生成简历" in result

    def test_generate_feedback_en_unchanged(self):
        from evaluation.ats_scorer import ATSScoreBreakdown
        from evaluation.feedback_generator import generate_feedback

        score = ATSScoreBreakdown(overall=0.5)
        result = generate_feedback(score, None, 0.5, language="en")

        assert "Previous attempt scored" in result
        assert "Please regenerate" in result


# ═══════════════════════════════════════════════════════════════════════
# 4. Chinese Quality Gate Tests
# ═══════════════════════════════════════════════════════════════════════


class TestChineseQualityGate:
    def test_heuristic_score_zh(self):
        from agents.quality_gate import _heuristic_score

        score, feedback = _heuristic_score(
            SAMPLE_ZH_RESUME_LATEX,
            SAMPLE_ZH_JD_ANALYSIS,
            language="zh",
        )
        assert 0.0 <= score <= 1.0
        # Good Chinese resume should score reasonably well
        assert score > 0.3

    def test_heuristic_score_zh_feedback_in_chinese(self):
        from agents.quality_gate import _heuristic_score

        score, feedback = _heuristic_score(
            r"\documentclass{article}\begin{document}简单\end{document}",
            {"required_skills": ["Python", "Go", "Kubernetes"]},
            language="zh",
        )
        # Feedback should be in Chinese for zh language
        has_zh = any(
            kw in feedback for kw in ["板块", "缺少", "简历", "建议", "动词", "量化"]
        )
        assert has_zh or feedback == "简历质量达标"

    def test_heuristic_score_en_unchanged(self):
        from agents.quality_gate import _heuristic_score

        score, feedback = _heuristic_score(
            r"\documentclass{article}\begin{document}simple\end{document}",
            {"required_skills": ["Python"]},
            language="en",
        )
        assert "简历" not in feedback  # No Chinese in English feedback

    @pytest.mark.asyncio
    async def test_quality_gate_node_passes_language(self):
        """quality_gate_node should pass language to scorer and feedback."""
        from agents.quality_gate import quality_gate_node

        state = {
            "task_number": 1,
            "latex_source": SAMPLE_ZH_RESUME_LATEX,
            "jd_analysis": SAMPLE_ZH_JD_ANALYSIS,
            "job_description": SAMPLE_ZH_JD,
            "language": "zh",
            "retry_count": 0,
        }

        result = await quality_gate_node(state)
        assert "quality_score" in result
        assert "quality_feedback" in result
        assert isinstance(result["quality_score"], float)


# ═══════════════════════════════════════════════════════════════════════
# 5. Chinese Agent Prompt Selection Tests
# ═══════════════════════════════════════════════════════════════════════


class TestChinesePromptSelection:
    @pytest.mark.asyncio
    async def test_jd_analyzer_uses_zh_prompt(self):
        from agents.jd_analyzer import JD_ANALYSIS_PROMPT_ZH, jd_analyzer_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value='{"job_title": "后端工程师", "company_name": "字节跳动", "required_skills": ["Python"], "preferred_skills": [], "experience_level": "3年", "key_responsibilities": [], "industry": "互联网"}')
        mock_provider.last_token_usage = None

        state = {
            "task_number": 1,
            "task_id": "test-zh",
            "job_description": SAMPLE_ZH_JD,
            "language": "zh",
            "provider_name": "gemini",
            "agent_outputs": {},
        }

        with patch("services.provider_registry.get_provider_for_agent", return_value=mock_provider):
            result = await jd_analyzer_agent(state)

        # Verify Chinese prompt was used
        called_prompt = mock_provider.generate.call_args[0][0]
        assert "分析以下职位描述" in called_prompt

    @pytest.mark.asyncio
    async def test_jd_analyzer_uses_en_prompt_for_english(self):
        from agents.jd_analyzer import jd_analyzer_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value='{"job_title": "Engineer", "company_name": "Co", "required_skills": ["Python"], "preferred_skills": [], "experience_level": "3y", "key_responsibilities": [], "industry": "Tech"}')
        mock_provider.last_token_usage = None

        state = {
            "task_number": 1,
            "task_id": "test-en",
            "job_description": "Looking for a Python developer",
            "language": "en",
            "provider_name": "gemini",
            "agent_outputs": {},
        }

        with patch("services.provider_registry.get_provider_for_agent", return_value=mock_provider):
            result = await jd_analyzer_agent(state)

        called_prompt = mock_provider.generate.call_args[0][0]
        assert "Analyze the following job description" in called_prompt

    @pytest.mark.asyncio
    async def test_relevance_matcher_uses_zh_prompt(self):
        from agents.relevance_matcher import relevance_matcher_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value='{"matched_skills": ["Python"], "missing_skills": [], "relevant_experiences": [], "emphasis_points": [], "match_score": 0.8}')
        mock_provider.last_token_usage = None

        state = {
            "task_number": 1,
            "task_id": "test-zh",
            "language": "zh",
            "provider_name": "gemini",
            "user_information": "我是一名有5年经验的软件工程师",
            "jd_analysis": SAMPLE_ZH_JD_ANALYSIS,
            "agent_outputs": {},
        }

        with patch("services.provider_registry.get_provider_for_agent", return_value=mock_provider):
            result = await relevance_matcher_agent(state)

        called_prompt = mock_provider.generate.call_args[0][0]
        assert "资深职业顾问" in called_prompt

    @pytest.mark.asyncio
    async def test_resume_writer_uses_zh_prefix(self):
        from agents.resume_writer import resume_writer_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value="\\documentclass{article}\\begin{document}简历\\end{document}"
        )
        mock_provider.last_token_usage = None

        mock_pm = MagicMock()
        mock_pm.get_resume_prompt_with_substitutions = MagicMock(return_value="base prompt")

        state = {
            "task_number": 1,
            "task_id": "test-zh",
            "job_description": SAMPLE_ZH_JD,
            "language": "zh",
            "template_id": "classic",
            "provider_name": "gemini",
            "jd_analysis": SAMPLE_ZH_JD_ANALYSIS,
            "relevance_match": {"matched_skills": ["Python"], "missing_skills": ["Go"], "emphasis_points": [], "match_score": 0.7},
            "retry_count": 0,
            "agent_outputs": {},
        }

        with (
            patch("services.provider_registry.get_provider_for_agent", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_pm),
        ):
            result = await resume_writer_agent(state)

        called_prompt = mock_provider.generate.call_args[0][0]
        assert "针对目标岗位的简历优化指令" in called_prompt
        assert "ATS关键词优化要求" in called_prompt

    @pytest.mark.asyncio
    async def test_cover_letter_writer_uses_zh_prefix(self):
        from agents.cover_letter_writer import cover_letter_writer_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value="尊敬的招聘经理...")
        mock_provider.last_token_usage = None

        mock_pm = MagicMock()
        mock_pm.get_cover_letter_prompt_with_substitutions = MagicMock(return_value="base")

        state = {
            "task_number": 1,
            "task_id": "test-zh",
            "job_description": SAMPLE_ZH_JD,
            "language": "zh",
            "provider_name": "gemini",
            "resume_text": "简历内容",
            "jd_analysis": SAMPLE_ZH_JD_ANALYSIS,
            "relevance_match": {"emphasis_points": ["Python"], "match_score": 0.7},
            "agent_outputs": {},
        }

        with (
            patch("services.provider_registry.get_provider_for_agent", return_value=mock_provider),
            patch("services.prompt_manager.get_prompt_manager", return_value=mock_pm),
        ):
            result = await cover_letter_writer_agent(state)

        called_prompt = mock_provider.generate.call_args[0][0]
        assert "针对目标岗位的求职信写作指令" in called_prompt

    @pytest.mark.asyncio
    async def test_company_researcher_uses_zh_prompt(self):
        from agents.company_researcher import auto_company_research_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value="字节跳动是一家领先的互联网公司...")
        mock_provider.last_token_usage = None

        state = {
            "task_number": 1,
            "task_id": "test-zh",
            "language": "zh",
            "provider_name": "gemini",
            "company_name": "字节跳动",
            "jd_analysis": SAMPLE_ZH_JD_ANALYSIS,
            "agent_outputs": {},
        }

        with patch("services.provider_registry.get_provider_for_agent", return_value=mock_provider):
            result = await auto_company_research_agent(state)

        called_prompt = mock_provider.generate.call_args[0][0]
        assert "调研公司" in called_prompt
        assert "字节跳动" in called_prompt

    @pytest.mark.asyncio
    async def test_company_researcher_zh_no_info_detection(self):
        from agents.company_researcher import auto_company_research_agent

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value="未找到可靠信息。")
        mock_provider.last_token_usage = None

        state = {
            "task_number": 1,
            "task_id": "test-zh",
            "language": "zh",
            "provider_name": "gemini",
            "company_name": "虚构公司",
            "jd_analysis": {"job_title": "工程师"},
            "agent_outputs": {},
        }

        with patch("services.provider_registry.get_provider_for_agent", return_value=mock_provider):
            result = await auto_company_research_agent(state)

        assert result["company_context"] is None


# ═══════════════════════════════════════════════════════════════════════
# 6. CJK PDF Support Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCJKPDFSupport:
    def test_cjk_text_detection(self):
        from services.text_to_pdf import _is_cjk_text

        assert _is_cjk_text("尊敬的招聘经理，我是一名软件工程师")
        assert _is_cjk_text("混合Mixed文本Text也算Chinese")
        assert not _is_cjk_text("This is purely English text")
        assert not _is_cjk_text("")

    def test_cjk_font_registration(self):
        from services.text_to_pdf import _register_cjk_font

        # Should either return a font name or None (depends on system)
        result = _register_cjk_font()
        assert result is None or isinstance(result, str)

    def test_convert_chinese_cover_letter(self, tmp_path):
        """Test that Chinese text can be converted to PDF."""
        from services.text_to_pdf import TextToPDFConverter

        converter = TextToPDFConverter()
        output = tmp_path / "cover_letter_zh.pdf"

        text = """张三
zhangsan@email.com
13800138000

2024年3月1日

尊敬的招聘经理：

您好！我是一名有5年工作经验的高级后端开发工程师，对贵公司的后端工程师岗位非常感兴趣。

在过去的工作经历中，我主导设计了多个大型分布式系统。

此致
敬礼

张三"""

        try:
            result = converter.convert(text, output)
            assert result.exists()
            assert result.stat().st_size > 0
        except Exception as e:
            # Font not available is acceptable in CI
            if "font" in str(e).lower() or "codec" in str(e).lower():
                pytest.skip(f"CJK font not available: {e}")
            raise


# ═══════════════════════════════════════════════════════════════════════
# 7. DeepSeek / Qwen Provider Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDeepSeekProvider:
    def test_provider_registry_has_deepseek(self):
        from services.provider_registry import AVAILABLE_PROVIDERS

        ids = [p["id"] for p in AVAILABLE_PROVIDERS]
        assert "deepseek" in ids

    def test_deepseek_client_properties(self):
        with patch("services.settings_manager.get_settings_manager") as mock_sm:
            mock_sm.return_value = MagicMock()
            mock_sm.return_value.get = MagicMock(return_value=None)

            from services.deepseek_client import DeepSeekClient

            client = DeepSeekClient()
            assert client.provider_name == "deepseek"
            assert client.model == "deepseek-chat"

    def test_deepseek_custom_model(self):
        with patch("services.deepseek_client.get_settings_manager") as mock_sm:
            mock_inst = MagicMock()
            mock_inst.get = MagicMock(side_effect=lambda k: "deepseek-reasoner" if k == "deepseek_model" else None)
            mock_sm.return_value = mock_inst

            from services.deepseek_client import DeepSeekClient

            client = DeepSeekClient()
            assert client.model == "deepseek-reasoner"

    def test_create_deepseek_via_registry(self):
        with (
            patch("services.deepseek_client.get_settings_manager") as mock_sm,
            patch("services.provider_registry._providers", {}),
        ):
            mock_inst = MagicMock()
            mock_inst.get = MagicMock(return_value=None)
            mock_sm.return_value = mock_inst

            from services.provider_registry import get_provider

            provider = get_provider("deepseek")
            assert provider.provider_name == "deepseek"


class TestQwenProvider:
    def test_provider_registry_has_qwen(self):
        from services.provider_registry import AVAILABLE_PROVIDERS

        ids = [p["id"] for p in AVAILABLE_PROVIDERS]
        assert "qwen" in ids

    def test_qwen_client_properties(self):
        with patch("services.settings_manager.get_settings_manager") as mock_sm:
            mock_sm.return_value = MagicMock()
            mock_sm.return_value.get = MagicMock(return_value=None)

            from services.qwen_client import QwenClient

            client = QwenClient()
            assert client.provider_name == "qwen"
            assert client.model == "qwen-plus"

    def test_qwen_custom_model(self):
        with patch("services.qwen_client.get_settings_manager") as mock_sm:
            mock_inst = MagicMock()
            mock_inst.get = MagicMock(side_effect=lambda k: "qwen-max" if k == "qwen_model" else None)
            mock_sm.return_value = mock_inst

            from services.qwen_client import QwenClient

            client = QwenClient()
            assert client.model == "qwen-max"

    def test_create_qwen_via_registry(self):
        with (
            patch("services.qwen_client.get_settings_manager") as mock_sm,
            patch("services.provider_registry._providers", {}),
        ):
            mock_inst = MagicMock()
            mock_inst.get = MagicMock(return_value=None)
            mock_sm.return_value = mock_inst

            from services.provider_registry import get_provider

            provider = get_provider("qwen")
            assert provider.provider_name == "qwen"


# ═══════════════════════════════════════════════════════════════════════
# 8. Config Tests
# ═══════════════════════════════════════════════════════════════════════


class TestConfigChanges:
    def test_deepseek_settings_exist(self):
        from config import Settings

        s = Settings()
        assert hasattr(s, "deepseek_api_key")
        assert hasattr(s, "deepseek_model")
        assert s.deepseek_model == "deepseek-chat"

    def test_qwen_settings_exist(self):
        from config import Settings

        s = Settings()
        assert hasattr(s, "qwen_api_key")
        assert hasattr(s, "qwen_model")
        assert s.qwen_model == "qwen-plus"

    def test_cover_letter_zh_font_settings(self):
        from config import Settings

        s = Settings()
        assert hasattr(s, "cover_letter_font_zh")
        assert hasattr(s, "cover_letter_font_zh_fallback")
        assert s.cover_letter_font_zh == "SimSun"
        assert s.cover_letter_font_zh_fallback == "Helvetica"
