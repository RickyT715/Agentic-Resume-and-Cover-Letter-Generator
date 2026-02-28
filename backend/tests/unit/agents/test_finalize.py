"""Tests for finalize node functions."""
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock


# ===================== _sanitize_filename =====================

class TestSanitizeFilename:
    def test_basic_sanitization(self):
        from agents.finalize import _sanitize_filename
        assert _sanitize_filename("Google") == "Google"

    def test_replaces_spaces_with_underscore(self):
        from agents.finalize import _sanitize_filename
        assert _sanitize_filename("Software Engineer") == "Software_Engineer"

    def test_replaces_hyphens_with_underscore(self):
        from agents.finalize import _sanitize_filename
        assert _sanitize_filename("Google-Engineer") == "Google_Engineer"

    def test_removes_special_chars(self):
        from agents.finalize import _sanitize_filename
        result = _sanitize_filename('File<>:"/\\|?*Name')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_collapses_multiple_underscores(self):
        from agents.finalize import _sanitize_filename
        result = _sanitize_filename("Too   Many   Spaces")
        assert "__" not in result

    def test_strips_leading_trailing_underscores(self):
        from agents.finalize import _sanitize_filename
        result = _sanitize_filename("_test_")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_truncates_long_names(self):
        from agents.finalize import _sanitize_filename
        result = _sanitize_filename("A" * 100)
        assert len(result) <= 50

    def test_empty_returns_unknown(self):
        from agents.finalize import _sanitize_filename
        assert _sanitize_filename("") == "Unknown"

    def test_special_chars_only_returns_unknown(self):
        from agents.finalize import _sanitize_filename
        assert _sanitize_filename("<>:?*") == "Unknown"


# ===================== compile_latex_node =====================

class TestCompileLatexNode:
    @pytest.mark.asyncio
    async def test_successful_compilation(self, sample_resume_state, tmp_path):
        from agents.finalize import compile_latex_node
        from services.latex_compiler import CompilationAttempt

        sample_resume_state["latex_source"] = (
            "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
        )

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4")

        mock_result = CompilationAttempt(
            attempt_number=1, latex_code="...", success=True, pdf_path=pdf_path
        )
        mock_compiler = MagicMock()
        mock_compiler.compile_once = MagicMock(return_value=mock_result)

        mock_settings = MagicMock()
        mock_settings.max_latex_retries = 3
        mock_settings.output_dir = tmp_path

        mock_sm = MagicMock()
        mock_sm.get.side_effect = lambda key, default=None: {
            "enforce_resume_one_page": False,
            "max_page_retry_attempts": 3,
        }.get(key, default)

        with patch("config.settings", mock_settings), \
             patch("services.latex_compiler.LaTeXCompiler", return_value=mock_compiler), \
             patch("services.settings_manager.get_settings_manager", return_value=mock_sm), \
             patch("services.latex_utils.process_latex_response", side_effect=lambda x: x), \
             patch("services.pdf_page_counter.validate_single_page", return_value=(True, 1)):
            result = await compile_latex_node(sample_resume_state)

        assert result["resume_pdf_path"] is not None
        assert result["current_node"] == "compile_latex"

    @pytest.mark.asyncio
    async def test_compilation_failure(self, sample_resume_state, tmp_path):
        from agents.finalize import compile_latex_node
        from services.latex_compiler import CompilationAttempt

        sample_resume_state["latex_source"] = (
            "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
        )

        mock_result = CompilationAttempt(
            attempt_number=1, latex_code="...", success=False, error_log="Error"
        )
        mock_compiler = MagicMock()
        mock_compiler.compile_once = MagicMock(return_value=mock_result)

        mock_settings = MagicMock()
        mock_settings.max_latex_retries = 1
        mock_settings.output_dir = tmp_path

        mock_sm = MagicMock()
        mock_sm.get.side_effect = lambda key, default=None: {
            "enforce_resume_one_page": False,
            "max_page_retry_attempts": 1,
        }.get(key, default)

        with patch("config.settings", mock_settings), \
             patch("services.latex_compiler.LaTeXCompiler", return_value=mock_compiler), \
             patch("services.settings_manager.get_settings_manager", return_value=mock_sm), \
             patch("services.latex_utils.process_latex_response", side_effect=lambda x: x), \
             patch("services.pdf_page_counter.validate_single_page", return_value=(True, 1)):
            result = await compile_latex_node(sample_resume_state)

        assert "error" in result
        assert "failed" in result["error"].lower()


# ===================== extract_text_node =====================

class TestExtractTextNode:
    @pytest.mark.asyncio
    async def test_extracts_text(self, sample_resume_state, tmp_path):
        from agents.finalize import extract_text_node

        sample_resume_state["resume_pdf_path"] = str(tmp_path / "test.pdf")

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = "Extracted resume text content"

        with patch("services.pdf_extractor.PDFTextExtractor", return_value=mock_extractor):
            result = await extract_text_node(sample_resume_state)

        assert result["resume_text"] == "Extracted resume text content"
        assert result["current_node"] == "extract_text"


# ===================== create_cover_letter_pdf_node =====================

class TestCreateCoverLetterPdfNode:
    @pytest.mark.asyncio
    async def test_creates_cover_pdf(self, sample_resume_state, tmp_path):
        from agents.finalize import create_cover_letter_pdf_node

        sample_resume_state["cover_letter_text"] = "Dear Hiring Manager..."
        sample_resume_state["company_name"] = "TestCo"
        sample_resume_state["position_name"] = "Engineer"

        mock_settings = MagicMock()
        mock_settings.output_dir = tmp_path

        mock_converter = MagicMock()

        mock_sm = MagicMock()
        mock_sm.get.return_value = False  # don't enforce one page

        with patch("config.settings", mock_settings), \
             patch("services.text_to_pdf.TextToPDFConverter", return_value=mock_converter), \
             patch("services.settings_manager.get_settings_manager", return_value=mock_sm), \
             patch("services.pdf_page_counter.validate_single_page", return_value=(True, 1)):
            result = await create_cover_letter_pdf_node(sample_resume_state)

        assert "cover_letter_pdf_path" in result
        assert result["current_node"] == "create_cover_pdf"
        mock_converter.convert.assert_called_once()


# ===================== finalize_node =====================

class TestFinalizeNode:
    @pytest.mark.asyncio
    async def test_copies_resume_to_final_location(self, sample_resume_state, tmp_path):
        from agents.finalize import finalize_node

        src_pdf = tmp_path / "src" / "resume.pdf"
        src_pdf.parent.mkdir(parents=True)
        src_pdf.write_bytes(b"%PDF-1.4")

        sample_resume_state["resume_pdf_path"] = str(src_pdf)
        sample_resume_state["company_name"] = "TestCo"
        sample_resume_state["position_name"] = "Engineer"

        mock_settings = MagicMock()
        mock_settings.output_dir = tmp_path / "output"

        with patch("config.settings", mock_settings):
            result = await finalize_node(sample_resume_state)

        assert result["resume_pdf_path"] is not None
        assert "resume_TestCo_Engineer" in result["resume_pdf_path"]
        assert result["current_node"] == "finalize"

    @pytest.mark.asyncio
    async def test_finalize_no_company_name(self, sample_resume_state, tmp_path):
        from agents.finalize import finalize_node

        src_pdf = tmp_path / "src" / "resume.pdf"
        src_pdf.parent.mkdir(parents=True)
        src_pdf.write_bytes(b"%PDF-1.4")

        sample_resume_state["resume_pdf_path"] = str(src_pdf)
        sample_resume_state["company_name"] = ""
        sample_resume_state["position_name"] = ""

        mock_settings = MagicMock()
        mock_settings.output_dir = tmp_path / "output"

        with patch("config.settings", mock_settings):
            result = await finalize_node(sample_resume_state)

        assert "resume_Resume" in result["resume_pdf_path"]
