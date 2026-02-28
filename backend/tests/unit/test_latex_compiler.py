"""Tests for LaTeX compiler service."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess


# ===================== CompilationAttempt / CompilationError =====================

class TestCompilationAttempt:
    def test_dataclass_fields(self):
        from services.latex_compiler import CompilationAttempt
        attempt = CompilationAttempt(
            attempt_number=1,
            latex_code="\\documentclass{article}",
            success=True,
            pdf_path=Path("/tmp/test.pdf"),
        )
        assert attempt.attempt_number == 1
        assert attempt.success is True
        assert attempt.error_log is None
        assert attempt.used_error_feedback is False

    def test_failed_attempt_with_error(self):
        from services.latex_compiler import CompilationAttempt
        attempt = CompilationAttempt(
            attempt_number=2,
            latex_code="bad latex",
            success=False,
            error_log="Undefined control sequence",
            used_error_feedback=True,
        )
        assert attempt.success is False
        assert "Undefined" in attempt.error_log


class TestCompilationError:
    def test_error_with_attempts(self):
        from services.latex_compiler import CompilationError, CompilationAttempt
        attempts = [
            CompilationAttempt(attempt_number=1, latex_code="code1", success=False, error_log="err1"),
            CompilationAttempt(attempt_number=2, latex_code="code2", success=False, error_log="err2"),
        ]
        err = CompilationError("Failed after 2 attempts", attempts)
        assert "Failed after 2 attempts" in str(err)
        assert len(err.attempts) == 2

    def test_debug_report(self):
        from services.latex_compiler import CompilationError, CompilationAttempt
        attempts = [
            CompilationAttempt(attempt_number=1, latex_code="code", success=False, error_log="err"),
        ]
        err = CompilationError("fail", attempts)
        report = err.get_debug_report()
        assert "LATEX COMPILATION FAILURE REPORT" in report
        assert "Attempt 1" in report


# ===================== LaTeXCompiler =====================

class TestLaTeXCompiler:
    def test_init_defaults(self):
        from services.latex_compiler import LaTeXCompiler
        compiler = LaTeXCompiler()
        assert compiler.max_retries == 3
        assert compiler.attempts == []

    def test_init_custom_retries(self):
        from services.latex_compiler import LaTeXCompiler
        compiler = LaTeXCompiler(max_retries=5)
        assert compiler.max_retries == 5

    def test_add_attempt(self):
        from services.latex_compiler import LaTeXCompiler, CompilationAttempt
        compiler = LaTeXCompiler()
        attempt = CompilationAttempt(attempt_number=1, latex_code="code", success=True)
        compiler.add_attempt(attempt)
        assert len(compiler.attempts) == 1

    def test_clear_attempts(self):
        from services.latex_compiler import LaTeXCompiler, CompilationAttempt
        compiler = LaTeXCompiler()
        compiler.add_attempt(CompilationAttempt(attempt_number=1, latex_code="code", success=True))
        compiler.clear_attempts()
        assert compiler.attempts == []

    def test_get_last_error_when_failed(self):
        from services.latex_compiler import LaTeXCompiler, CompilationAttempt
        compiler = LaTeXCompiler()
        compiler.add_attempt(CompilationAttempt(
            attempt_number=1, latex_code="code", success=False, error_log="some error"
        ))
        assert compiler.get_last_error() == "some error"

    def test_get_last_error_when_success(self):
        from services.latex_compiler import LaTeXCompiler, CompilationAttempt
        compiler = LaTeXCompiler()
        compiler.add_attempt(CompilationAttempt(
            attempt_number=1, latex_code="code", success=True
        ))
        assert compiler.get_last_error() is None

    def test_get_last_error_empty(self):
        from services.latex_compiler import LaTeXCompiler
        compiler = LaTeXCompiler()
        assert compiler.get_last_error() is None

    def test_get_last_latex(self):
        from services.latex_compiler import LaTeXCompiler, CompilationAttempt
        compiler = LaTeXCompiler()
        compiler.add_attempt(CompilationAttempt(
            attempt_number=1, latex_code="my latex", success=True
        ))
        assert compiler.get_last_latex() == "my latex"

    def test_get_last_latex_empty(self):
        from services.latex_compiler import LaTeXCompiler
        compiler = LaTeXCompiler()
        assert compiler.get_last_latex() is None


class TestCompileOnce:
    def test_rejects_code_not_starting_with_documentclass(self):
        from services.latex_compiler import LaTeXCompiler
        with patch("config.settings") as mock_settings:
            mock_settings.logs_dir = Path("/tmp")
            compiler = LaTeXCompiler()
            result = compiler.compile_once("invalid code", "test", 1)
            assert result.success is False
            assert "documentclass" in result.error_log

    def test_rejects_code_not_ending_with_end_document(self):
        from services.latex_compiler import LaTeXCompiler
        with patch("config.settings") as mock_settings:
            mock_settings.logs_dir = Path("/tmp")
            compiler = LaTeXCompiler()
            result = compiler.compile_once("\\documentclass{article}\n\\begin{document}\nHello", "test", 1)
            assert result.success is False
            assert "end{document}" in result.error_log

    def test_successful_compilation(self, tmp_path):
        from services.latex_compiler import LaTeXCompiler
        latex = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"

        with patch("config.settings") as mock_settings:
            mock_settings.logs_dir = tmp_path / "logs"
            mock_settings.logs_dir.mkdir()
            mock_settings.output_dir = tmp_path / "output"
            mock_settings.output_dir.mkdir()

            def fake_run(args, **kwargs):
                # Simulate pdflatex creating a PDF
                output_dir = None
                for arg in args:
                    if arg.startswith("-output-directory="):
                        output_dir = arg.split("=", 1)[1]
                if output_dir:
                    # Find the tex filename
                    tex_file = [a for a in args if a.endswith(".tex")]
                    if tex_file:
                        stem = Path(tex_file[0]).stem
                        (Path(output_dir) / f"{stem}.pdf").write_bytes(b"%PDF-1.4 fake")
                return MagicMock(returncode=0, stdout="", stderr="")

            with patch("subprocess.run", side_effect=fake_run):
                compiler = LaTeXCompiler()
                result = compiler.compile_once(latex, "test", 1)
                assert result.success is True
                assert result.pdf_path is not None

    def test_compilation_timeout(self, tmp_path):
        from services.latex_compiler import LaTeXCompiler
        latex = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"

        with patch("config.settings") as mock_settings:
            mock_settings.logs_dir = tmp_path / "logs"
            mock_settings.logs_dir.mkdir()

            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pdflatex", 60)):
                compiler = LaTeXCompiler()
                result = compiler.compile_once(latex, "test", 1)
                assert result.success is False
                assert "timed out" in result.error_log

    def test_compiler_not_found(self, tmp_path):
        from services.latex_compiler import LaTeXCompiler
        latex = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"

        with patch("config.settings") as mock_settings:
            mock_settings.logs_dir = tmp_path / "logs"
            mock_settings.logs_dir.mkdir()

            with patch("subprocess.run", side_effect=FileNotFoundError):
                compiler = LaTeXCompiler()
                result = compiler.compile_once(latex, "test", 1)
                assert result.success is False
                assert "not found" in result.error_log

    def test_pdf_not_created(self, tmp_path):
        from services.latex_compiler import LaTeXCompiler
        latex = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"

        with patch("config.settings") as mock_settings:
            mock_settings.logs_dir = tmp_path / "logs"
            mock_settings.logs_dir.mkdir()
            mock_settings.output_dir = tmp_path / "output"
            mock_settings.output_dir.mkdir()

            with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="error", stderr="")):
                compiler = LaTeXCompiler()
                result = compiler.compile_once(latex, "test", 1)
                assert result.success is False
