"""Tests for the evaluation module (ATS scorer, feedback generator)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evaluation.ats_scorer import ATSScoreBreakdown, score_resume
from evaluation.feedback_generator import compute_combined_score, generate_feedback


GOOD_RESUME_LATEX = r"""
\documentclass[letterpaper,10pt]{article}
\begin{document}
\section{Summary}
Experienced software engineer with 7+ years building scalable distributed systems.

\section{Experience}
\textbf{Senior Software Engineer} | Google | 2020--Present
\begin{itemize}
\item Led development of a microservices platform, improving deployment speed by 40\%
\item Developed CI/CD pipelines reducing release cycles from 2 weeks to 2 hours
\item Managed a team of 5 engineers delivering 3+ major features per quarter
\item Architected real-time data processing system handling 10M events/day
\end{itemize}

\textbf{Software Engineer} | Meta | 2017--2020
\begin{itemize}
\item Built recommendation engine serving 50M+ users daily
\item Implemented ML pipeline achieving 95\% accuracy
\item Reduced API latency by 60\% through caching optimizations
\end{itemize}

\section{Education}
\textbf{M.S. Computer Science} | Stanford University | 2017

\section{Skills}
Python, Java, Go, Docker, Kubernetes, AWS, GCP, PostgreSQL, Redis, Kafka

\section{Projects}
\textbf{Open Source Contributor} -- Built real-time analytics dashboard (\href{https://github.com}{GitHub})
\end{document}
"""

MINIMAL_RESUME_LATEX = r"""
\documentclass{article}
\begin{document}
I did some work.
\end{document}
"""


class TestATSScorer:
    def test_good_resume_scores_high(self):
        jd = "Looking for a Senior Software Engineer with Python, Docker, Kubernetes, and AWS experience. 5+ years required."
        jd_analysis = {
            "required_skills": ["Python", "Docker", "Kubernetes", "AWS"],
            "preferred_skills": ["Go", "PostgreSQL"],
            "experience_level": "5+ years",
        }
        result = score_resume(GOOD_RESUME_LATEX, jd, jd_analysis)
        assert result.overall > 0.6
        assert result.keyword_match > 0.5
        assert len(result.matched_keywords) > 0

    def test_minimal_resume_scores_low(self):
        jd = "Software Engineer with Python and Java"
        jd_analysis = {
            "required_skills": ["Python", "Java", "AWS"],
            "experience_level": "3 years",
        }
        result = score_resume(MINIMAL_RESUME_LATEX, jd, jd_analysis)
        assert result.overall < 0.5
        assert len(result.feedback) > 0

    def test_action_verbs_detected(self):
        result = score_resume(GOOD_RESUME_LATEX, "SWE role", {})
        assert result.action_verbs > 0.5

    def test_quantified_achievements_detected(self):
        result = score_resume(GOOD_RESUME_LATEX, "SWE role", {})
        assert result.readability > 0.5

    def test_sections_detected(self):
        result = score_resume(GOOD_RESUME_LATEX, "SWE role", {})
        assert result.section_completeness > 0.5

    def test_missing_skills_in_feedback(self):
        jd_analysis = {
            "required_skills": ["Rust", "Haskell", "Erlang"],
            "experience_level": "5 years",
        }
        result = score_resume(GOOD_RESUME_LATEX, "FP engineer", jd_analysis)
        assert len(result.missing_keywords) > 0
        assert any("Missing" in f for f in result.feedback)

    def test_no_jd_analysis_fallback(self):
        result = score_resume(GOOD_RESUME_LATEX, "Software engineer with Python and Docker experience", None)
        assert 0 <= result.overall <= 1
        assert result.keyword_match >= 0


class TestCombinedScore:
    def test_ats_only(self):
        score = compute_combined_score(0.8, None)
        assert score == 0.8

    def test_combined_weighted(self):
        score = compute_combined_score(0.8, 0.6, ats_weight=0.6)
        expected = 0.8 * 0.6 + 0.6 * 0.4
        assert abs(score - expected) < 0.01

    def test_equal_weights(self):
        score = compute_combined_score(0.5, 0.5, ats_weight=0.5)
        assert score == 0.5


class TestFeedbackGenerator:
    def test_generates_feedback(self):
        ats = ATSScoreBreakdown(
            keyword_match=0.4,
            experience_alignment=0.6,
            format_score=0.7,
            action_verbs=0.3,
            readability=0.2,
            section_completeness=0.8,
            overall=0.45,
            matched_keywords=["Python", "Docker"],
            missing_keywords=["Kubernetes", "AWS", "Go"],
            feedback=["Missing 3 required skills", "Use more action verbs"],
        )
        feedback = generate_feedback(ats, None, 0.45)
        assert "0.45" in feedback
        assert "Kubernetes" in feedback
        assert "action verbs" in feedback.lower() or "Action Verbs" in feedback

    def test_includes_llm_feedback(self):
        from evaluation.llm_judge import LLMJudgeResult

        ats = ATSScoreBreakdown(overall=0.5, feedback=[])
        llm = LLMJudgeResult(
            overall_score=0.6,
            reasoning="Good but needs improvement",
            improvements=["Add metrics", "Use stronger verbs"],
        )
        feedback = generate_feedback(ats, llm, 0.54)
        assert "Expert Reviewer" in feedback
        assert "Add metrics" in feedback
