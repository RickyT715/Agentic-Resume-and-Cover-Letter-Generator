"""Tests for the quality gate node."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agents.quality_gate import _heuristic_score, quality_gate_node, should_retry


class TestHeuristicScore:
    def test_good_resume_scores_high(self):
        latex = r"""
        \documentclass{article}
        \begin{document}
        \section{Experience}
        Led development of a microservices platform, improving deployment speed by 40%.
        Developed CI/CD pipelines reducing release cycles from weeks to hours.
        Managed a team of 5 engineers delivering 3 major features.
        \section{Education}
        B.S. in Computer Science
        \section{Skills}
        Python, JavaScript, Docker, Kubernetes, AWS
        \section{Projects}
        Built real-time analytics dashboard serving 10,000+ users daily.
        Implemented machine learning pipeline achieving 95% accuracy.
        \end{document}
        """
        jd = {
            "required_skills": ["Python", "Docker", "AWS", "CI/CD"],
            "job_title": "Software Engineer",
        }
        score, feedback = _heuristic_score(latex, jd)
        assert score > 0.5

    def test_empty_resume_scores_low(self):
        latex = r"\documentclass{article}\begin{document}\end{document}"
        jd = {"required_skills": ["Python", "Java"], "job_title": "SWE"}
        score, feedback = _heuristic_score(latex, jd)
        assert score < 0.5
        assert feedback != ""

    def test_missing_skills_feedback(self):
        latex = r"\documentclass{article}\begin{document}\section{Experience}Did stuff.\end{document}"
        jd = {"required_skills": ["Rust", "Go", "Kubernetes"], "job_title": "SRE"}
        score, feedback = _heuristic_score(latex, jd)
        assert "Missing key skills" in feedback or "skills" in feedback.lower()

    def test_no_jd_skills_uses_default(self):
        latex = r"\documentclass{article}\begin{document}\section{Experience}Work.\section{Education}Degree.\section{Skills}Python.\end{document}"
        jd = {"required_skills": [], "job_title": "Developer"}
        score, feedback = _heuristic_score(latex, jd)
        assert score > 0.3  # Should still get reasonable score


class TestQualityGateNode:
    @pytest.mark.asyncio
    async def test_passes_good_score(self):
        state = {
            "task_number": 1,
            "latex_source": r"""
            \documentclass{article}
            \begin{document}
            \section{Experience}Led team of 10, improved performance by 50%.
            \section{Education}MS CS Stanford.
            \section{Skills}Python, Java, AWS, Docker, Kubernetes.
            \section{Projects}Built system serving 1M users.
            \end{document}
            """,
            "jd_analysis": {
                "required_skills": ["Python", "AWS", "Docker"],
                "job_title": "SWE",
            },
            "retry_count": 0,
            "agent_outputs": {},
        }
        result = await quality_gate_node(state)
        assert "quality_score" in result
        assert "quality_passed" in result

    @pytest.mark.asyncio
    async def test_max_retries_forces_pass(self):
        state = {
            "task_number": 1,
            "latex_source": r"\documentclass{article}\begin{document}bad\end{document}",
            "jd_analysis": {"required_skills": ["Rust", "Go"], "job_title": "SRE"},
            "retry_count": 2,
            "agent_outputs": {},
        }
        result = await quality_gate_node(state)
        assert result["quality_passed"] is True


class TestShouldRetry:
    def test_passes_goes_to_compile(self):
        state = {"quality_passed": True}
        assert should_retry(state) == "compile_latex"

    def test_fails_goes_to_resume_writer(self):
        state = {"quality_passed": False}
        assert should_retry(state) == "resume_writer"

    def test_default_passes(self):
        state = {}
        assert should_retry(state) == "compile_latex"
