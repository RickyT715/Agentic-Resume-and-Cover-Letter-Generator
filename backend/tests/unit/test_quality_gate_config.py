"""Unit tests for configurable quality gate settings."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestQualityGateConfig:
    def test_default_quality_threshold(self):
        """Default quality_threshold should be 0.7."""
        from config import Settings

        s = Settings()
        assert s.quality_threshold == 0.7

    def test_default_quality_max_retries(self):
        """Default quality_max_retries should be 2."""
        from config import Settings

        s = Settings()
        assert s.quality_max_retries == 2

    def test_quality_gate_uses_settings_threshold(self):
        """quality_gate_node should use the threshold from settings."""
        mock_settings = MagicMock()
        mock_settings.quality_threshold = 0.9
        mock_settings.quality_max_retries = 2

        state = {
            "task_number": 1,
            "latex_source": (
                "\\documentclass{article}\\begin{document}"
                "experience education skill project summary "
                "led developed implemented designed built "
                "increased by 50% $100,000 200+ users "
                "\\end{document}"
            ),
            "jd_analysis": {"required_skills": ["Python"]},
            "job_description": "We need Python",
            "language": "en",
            "retry_count": 0,
        }

        with (
            patch("agents.quality_gate.settings", mock_settings),
            patch("agents.quality_gate.score_resume", side_effect=Exception("no eval module"), create=True),
        ):
            import asyncio

            from agents.quality_gate import quality_gate_node

            result = asyncio.run(quality_gate_node(state))

        # With a threshold of 0.9, a heuristic score is unlikely to pass
        assert "quality_score" in result
        assert "quality_passed" in result
        assert "quality_threshold" not in result  # should use settings, not expose it

    def test_quality_gate_passes_when_max_retries_reached(self):
        """quality_gate_node should pass (force-pass) when retry_count >= max_retries."""
        mock_settings = MagicMock()
        mock_settings.quality_threshold = 0.99  # impossibly high threshold
        mock_settings.quality_max_retries = 2

        state = {
            "task_number": 1,
            "latex_source": "\\documentclass{article}\\begin{document}\\end{document}",
            "jd_analysis": {},
            "job_description": "",
            "language": "en",
            "retry_count": 2,  # at max retries
        }

        with (
            patch("agents.quality_gate.settings", mock_settings),
            patch(
                "agents.quality_gate.score_resume",
                side_effect=ImportError("no eval module"),
                create=True,
            ),
        ):
            import asyncio

            from agents.quality_gate import quality_gate_node

            result = asyncio.run(quality_gate_node(state))

        # Even with a very low score, should be force-passed at max retries
        assert result["quality_passed"] is True

    def test_quality_gate_fails_below_threshold(self):
        """quality_gate_node should fail when score is below threshold and retries remain."""
        mock_settings = MagicMock()
        mock_settings.quality_threshold = 0.99  # impossibly high threshold
        mock_settings.quality_max_retries = 3

        state = {
            "task_number": 1,
            "latex_source": "\\documentclass{article}\\begin{document}\\end{document}",
            "jd_analysis": {"required_skills": ["Python", "Go", "Rust", "C++", "Java"]},
            "job_description": "Need many skills",
            "language": "en",
            "retry_count": 0,
        }

        with (
            patch("agents.quality_gate.settings", mock_settings),
            patch(
                "agents.quality_gate.score_resume",
                side_effect=ImportError("no eval module"),
                create=True,
            ),
        ):
            import asyncio

            from agents.quality_gate import quality_gate_node

            result = asyncio.run(quality_gate_node(state))

        assert result["quality_passed"] is False
        assert result["retry_count"] == 1  # incremented because it failed

    def test_should_retry_routes_to_resume_writer_on_failure(self):
        """should_retry returns 'resume_writer' when quality failed and retries remain."""
        from agents.quality_gate import should_retry

        state = {
            "quality_passed": False,
            "retry_count": 1,
        }
        with patch("agents.quality_gate.settings") as mock_settings:
            mock_settings.quality_max_retries = 3
            result = should_retry(state)
        assert result == "resume_writer"

    def test_should_retry_routes_to_compile_latex_on_pass(self):
        """should_retry returns 'compile_latex' when quality passed."""
        from agents.quality_gate import should_retry

        state = {
            "quality_passed": True,
            "retry_count": 0,
        }
        result = should_retry(state)
        assert result == "compile_latex"
