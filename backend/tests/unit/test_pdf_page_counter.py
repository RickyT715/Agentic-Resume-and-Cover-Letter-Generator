"""Tests for PDF page counter utility."""

from unittest.mock import MagicMock, patch


class TestGetPdfPageCount:
    def test_returns_none_for_nonexistent_file(self, tmp_path):
        from services.pdf_page_counter import get_pdf_page_count

        result = get_pdf_page_count(tmp_path / "nonexistent.pdf")
        assert result is None

    def test_fitz_method_success(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake pdf")
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        with patch("services.pdf_page_counter._get_page_count_fitz", return_value=3):
            from services.pdf_page_counter import get_pdf_page_count

            assert get_pdf_page_count(pdf) == 3

    def test_fallback_to_pdfinfo(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake pdf")
        with (
            patch("services.pdf_page_counter._get_page_count_fitz", return_value=None),
            patch("services.pdf_page_counter._get_page_count_pdfinfo", return_value=2),
        ):
            from services.pdf_page_counter import get_pdf_page_count

            assert get_pdf_page_count(pdf) == 2

    def test_fallback_to_pypdf2(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake pdf")
        with (
            patch("services.pdf_page_counter._get_page_count_fitz", return_value=None),
            patch("services.pdf_page_counter._get_page_count_pdfinfo", return_value=None),
            patch("services.pdf_page_counter._get_page_count_pypdf2", return_value=1),
        ):
            from services.pdf_page_counter import get_pdf_page_count

            assert get_pdf_page_count(pdf) == 1

    def test_all_methods_fail(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake pdf")
        with (
            patch("services.pdf_page_counter._get_page_count_fitz", return_value=None),
            patch("services.pdf_page_counter._get_page_count_pdfinfo", return_value=None),
            patch("services.pdf_page_counter._get_page_count_pypdf2", return_value=None),
        ):
            from services.pdf_page_counter import get_pdf_page_count

            assert get_pdf_page_count(pdf) is None


class TestGetPageCountFitz:
    def test_fitz_success(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=5)
        with patch.dict("sys.modules", {"fitz": MagicMock()}):
            import sys

            sys.modules["fitz"].open = MagicMock(return_value=mock_doc)
            from services.pdf_page_counter import _get_page_count_fitz

            result = _get_page_count_fitz(pdf)
            assert result == 5

    def test_fitz_import_error(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        with patch.dict("sys.modules", {"fitz": None}):
            from services.pdf_page_counter import _get_page_count_fitz

            # When fitz module is None, import will fail
            result = _get_page_count_fitz(pdf)
            assert result is None


class TestGetPageCountPdfinfo:
    def test_pdfinfo_success(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Title: Test\nPages:          4\nOther: info\n"
        with patch("subprocess.run", return_value=mock_result):
            from services.pdf_page_counter import _get_page_count_pdfinfo

            assert _get_page_count_pdfinfo(pdf) == 4

    def test_pdfinfo_not_found(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        with patch("subprocess.run", side_effect=FileNotFoundError):
            from services.pdf_page_counter import _get_page_count_pdfinfo

            assert _get_page_count_pdfinfo(pdf) is None

    def test_pdfinfo_timeout(self, tmp_path):
        import subprocess

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pdfinfo", 10)):
            from services.pdf_page_counter import _get_page_count_pdfinfo

            assert _get_page_count_pdfinfo(pdf) is None

    def test_pdfinfo_nonzero_return(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            from services.pdf_page_counter import _get_page_count_pdfinfo

            assert _get_page_count_pdfinfo(pdf) is None


class TestValidateSinglePage:
    def test_single_page_passes(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        with patch("services.pdf_page_counter.get_pdf_page_count", return_value=1):
            from services.pdf_page_counter import validate_single_page

            is_single, count = validate_single_page(pdf)
            assert is_single is True
            assert count == 1

    def test_multi_page_fails(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        with patch("services.pdf_page_counter.get_pdf_page_count", return_value=3):
            from services.pdf_page_counter import validate_single_page

            is_single, count = validate_single_page(pdf)
            assert is_single is False
            assert count == 3

    def test_unknown_page_count_allows_continuation(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"fake")
        with patch("services.pdf_page_counter.get_pdf_page_count", return_value=None):
            from services.pdf_page_counter import validate_single_page

            is_single, count = validate_single_page(pdf)
            assert is_single is True
            assert count == 0
