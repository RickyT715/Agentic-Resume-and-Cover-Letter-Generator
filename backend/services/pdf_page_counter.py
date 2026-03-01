"""
PDF Page Counter Utility
Provides functionality to count pages in PDF files.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_pdf_page_count(pdf_path: Path) -> int | None:
    """
    Get the number of pages in a PDF file.

    Uses PyMuPDF (fitz) if available, otherwise falls back to other methods.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Number of pages, or None if unable to determine
    """
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return None

    # Method 1: Try PyMuPDF (fitz) - already a dependency
    page_count = _get_page_count_fitz(pdf_path)
    if page_count is not None:
        return page_count

    # Method 2: Try pdfinfo (from poppler-utils)
    page_count = _get_page_count_pdfinfo(pdf_path)
    if page_count is not None:
        return page_count

    # Method 3: Try PyPDF2
    page_count = _get_page_count_pypdf2(pdf_path)
    if page_count is not None:
        return page_count

    logger.warning(f"Could not determine page count for {pdf_path}")
    return None


def _get_page_count_fitz(pdf_path: Path) -> int | None:
    """Get page count using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        count = len(doc)
        doc.close()
        logger.debug(f"fitz: {pdf_path} has {count} pages")
        return count
    except ImportError:
        logger.debug("PyMuPDF (fitz) not available")
    except Exception as e:
        logger.debug(f"fitz error: {e}")

    return None


def _get_page_count_pdfinfo(pdf_path: Path) -> int | None:
    """Get page count using pdfinfo from poppler-utils."""
    try:
        result = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("Pages:"):
                    count = int(line.split(":")[1].strip())
                    logger.debug(f"pdfinfo: {pdf_path} has {count} pages")
                    return count
    except FileNotFoundError:
        logger.debug("pdfinfo not available")
    except subprocess.TimeoutExpired:
        logger.warning("pdfinfo timed out")
    except Exception as e:
        logger.debug(f"pdfinfo error: {e}")

    return None


def _get_page_count_pypdf2(pdf_path: Path) -> int | None:
    """Get page count using PyPDF2."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(pdf_path))
        count = len(reader.pages)
        logger.debug(f"PyPDF2: {pdf_path} has {count} pages")
        return count
    except ImportError:
        logger.debug("PyPDF2 not available")
    except Exception as e:
        logger.debug(f"PyPDF2 error: {e}")

    return None


def validate_single_page(pdf_path: Path) -> tuple[bool, int]:
    """
    Validate that a PDF is exactly one page.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Tuple of (is_single_page, actual_page_count)
        If page count cannot be determined, returns (True, 0) to allow continuation
    """
    page_count = get_pdf_page_count(pdf_path)

    if page_count is None:
        logger.warning(f"Could not validate page count for {pdf_path}, allowing to continue")
        return (True, 0)

    is_single = page_count == 1
    if not is_single:
        logger.warning(f"PDF {pdf_path} has {page_count} pages (expected 1)")

    return (is_single, page_count)
