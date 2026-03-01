"""Tests for PDF text extractor."""

from unittest.mock import MagicMock, patch

import pytest


class TestPDFTextExtractor:
    def test_extract_single_page(self, tmp_path):
        from services.pdf_extractor import PDFTextExtractor

        mock_page = MagicMock()
        mock_page.get_text.return_value = "Hello World"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        with patch("services.pdf_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            extractor = PDFTextExtractor()
            result = extractor.extract(tmp_path / "test.pdf")
            assert result == "Hello World"

    def test_extract_multi_page(self, tmp_path):
        from services.pdf_extractor import PDFTextExtractor

        page1 = MagicMock()
        page1.get_text.return_value = "Page 1 content"
        page2 = MagicMock()
        page2.get_text.return_value = "Page 2 content"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([page1, page2]))

        with patch("services.pdf_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            extractor = PDFTextExtractor()
            result = extractor.extract(tmp_path / "test.pdf")
            assert "Page 1 content" in result
            assert "Page 2 content" in result
            assert "\n" in result

    def test_extract_empty_pdf(self, tmp_path):
        from services.pdf_extractor import PDFTextExtractor

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([]))

        with patch("services.pdf_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            extractor = PDFTextExtractor()
            result = extractor.extract(tmp_path / "test.pdf")
            assert result == ""

    def test_extract_raises_on_corrupt_file(self, tmp_path):
        from services.pdf_extractor import PDFTextExtractor

        with patch("services.pdf_extractor.fitz") as mock_fitz:
            mock_fitz.open.side_effect = Exception("Cannot open file")
            extractor = PDFTextExtractor()
            with pytest.raises(Exception, match="Cannot open file"):
                extractor.extract(tmp_path / "corrupt.pdf")

    def test_doc_close_called(self, tmp_path):
        from services.pdf_extractor import PDFTextExtractor

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([]))

        with patch("services.pdf_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            extractor = PDFTextExtractor()
            extractor.extract(tmp_path / "test.pdf")
            mock_doc.close.assert_called_once()

    def test_extract_strips_whitespace(self, tmp_path):
        from services.pdf_extractor import PDFTextExtractor

        mock_page = MagicMock()
        mock_page.get_text.return_value = "  Content with spaces  "
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        with patch("services.pdf_extractor.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            extractor = PDFTextExtractor()
            result = extractor.extract(tmp_path / "test.pdf")
            assert result == "Content with spaces"
