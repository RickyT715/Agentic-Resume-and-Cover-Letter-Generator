"""Tests for LaTeX utilities (extract_metadata, extract_latex, post_process_latex)."""

import pytest

# ===================== extract_metadata =====================


class TestExtractMetadata:
    def test_extracts_company_and_position(self):
        from services.latex_utils import extract_metadata

        text = (
            "% META_COMPANY: Google\n"
            "% META_POSITION: Software Engineer\n"
            "\\documentclass{article}\n\\begin{document}\\end{document}"
        )
        meta = extract_metadata(text)
        assert meta["company_name"] == "Google"
        assert meta["position_name"] == "Software Engineer"

    def test_extracts_company_only(self):
        from services.latex_utils import extract_metadata

        text = "% META_COMPANY: Apple\n\\documentclass{article}"
        meta = extract_metadata(text)
        assert meta["company_name"] == "Apple"
        assert meta["position_name"] == ""

    def test_no_metadata(self):
        from services.latex_utils import extract_metadata

        text = "\\documentclass{article}\n\\begin{document}\\end{document}"
        meta = extract_metadata(text)
        assert meta["company_name"] == ""
        assert meta["position_name"] == ""

    def test_no_documentclass(self):
        from services.latex_utils import extract_metadata

        meta = extract_metadata("No latex here")
        assert meta == {"company_name": "", "position_name": ""}

    def test_metadata_with_extra_spaces(self):
        from services.latex_utils import extract_metadata

        text = "%   META_COMPANY:   SpaceX   \n\\documentclass{article}"
        meta = extract_metadata(text)
        assert meta["company_name"] == "SpaceX"

    def test_metadata_after_documentclass_ignored(self):
        from services.latex_utils import extract_metadata

        text = "\\documentclass{article}\n% META_COMPANY: Ignored"
        meta = extract_metadata(text)
        assert meta["company_name"] == ""


# ===================== extract_latex =====================


class TestExtractLatex:
    def test_extracts_plain_latex(self):
        from services.latex_utils import extract_latex

        text = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
        result = extract_latex(text)
        assert result.startswith("\\documentclass")
        assert result.endswith("\\end{document}")

    def test_extracts_from_markdown_block(self):
        from services.latex_utils import extract_latex

        text = "Here is the latex:\n```latex\n\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n```\nDone."
        result = extract_latex(text)
        assert result.startswith("\\documentclass")
        assert result.endswith("\\end{document}")

    def test_extracts_from_generic_code_block(self):
        from services.latex_utils import extract_latex

        text = "```\n\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n```"
        result = extract_latex(text)
        assert "Hello" in result

    def test_strips_text_before_documentclass(self):
        from services.latex_utils import extract_latex

        text = "Some preamble text\n\\documentclass{article}\n\\begin{document}\nBody\n\\end{document}"
        result = extract_latex(text)
        assert result.startswith("\\documentclass")
        assert "Some preamble" not in result

    def test_strips_text_after_end_document(self):
        from services.latex_utils import extract_latex

        text = "\\documentclass{article}\n\\begin{document}\nBody\n\\end{document}\n\nSome trailing text"
        result = extract_latex(text)
        assert result.endswith("\\end{document}")
        assert "trailing" not in result

    def test_uses_last_end_document(self):
        from services.latex_utils import extract_latex

        text = "\\documentclass{article}\n\\begin{document}\n\\end{document}\n% Extra\n\\end{document}"
        result = extract_latex(text)
        assert result.endswith("\\end{document}")

    def test_raises_on_missing_documentclass(self):
        from services.latex_utils import extract_latex

        with pytest.raises(ValueError, match="missing.*documentclass"):
            extract_latex("\\begin{document}\nHello\n\\end{document}")

    def test_raises_on_missing_end_document(self):
        from services.latex_utils import extract_latex

        with pytest.raises(ValueError, match="missing.*end"):
            extract_latex("\\documentclass{article}\n\\begin{document}\nHello")

    def test_raises_on_empty_string(self):
        from services.latex_utils import extract_latex

        with pytest.raises(ValueError):
            extract_latex("")


# ===================== post_process_latex =====================


class TestPostProcessLatex:
    def test_changes_11pt_to_10pt(self):
        from services.latex_utils import post_process_latex

        code = "\\documentclass[letterpaper, 11pt]{article}\n\\begin{document}\\end{document}"
        result = post_process_latex(code)
        assert "10pt" in result
        assert "11pt" not in result

    def test_fixes_labelitemii_circ_dollar(self):
        from services.latex_utils import post_process_latex

        code = "\\renewcommand{\\labelitemii}{{\\circ$}}"
        result = post_process_latex(code)
        assert "$\\circ$" in result

    def test_fixes_labelitemii_dollar_circ(self):
        from services.latex_utils import post_process_latex

        code = "\\renewcommand{\\labelitemii}{{$\\circ}}"
        result = post_process_latex(code)
        assert "$\\circ$" in result

    def test_fixes_less_than_before_digit(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("Latency <1s")
        assert "$<$1s" in result

    def test_fixes_greater_than_before_digit(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("Improved by >50\\%")
        assert "$>$50" in result

    def test_fixes_less_than_between_spaces(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("A < B")
        assert "$<$" in result

    def test_fixes_greater_than_between_spaces(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("A > B")
        assert "$>$" in result

    def test_fixes_empty_href(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("\\href{}{Click here}")
        assert "\\textbf{Click here}" in result

    def test_fixes_double_dollar_circ(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("$$\\circ$$")
        assert result.strip() == "$\\circ$"

    def test_fixes_double_dollar_less_than(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("$$<$$")
        assert "$<$" in result

    def test_escapes_unescaped_hash(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("C# programming")
        assert "C\\#" in result

    def test_does_not_escape_already_escaped_hash(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("C\\# programming")
        assert "C\\# programming" in result

    def test_escapes_unescaped_ampersand_in_text(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("AT&T")
        assert "AT\\&T" in result

    def test_strips_leading_trailing_blank_lines(self):
        from services.latex_utils import post_process_latex

        result = post_process_latex("\n\n\\documentclass{article}\n\\end{document}\n\n")
        assert result.startswith("\\documentclass")
        assert result.endswith("\\end{document}")


# ===================== process_latex_response =====================


class TestProcessLatexResponse:
    def test_combined_extract_and_postprocess(self):
        from services.latex_utils import process_latex_response

        raw = "```latex\n\\documentclass[letterpaper, 11pt]{article}\n\\begin{document}\nHello\n\\end{document}\n```"
        result = process_latex_response(raw)
        assert result.startswith("\\documentclass")
        assert "10pt" in result
