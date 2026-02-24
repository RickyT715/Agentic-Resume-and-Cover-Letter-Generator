import fitz  # PyMuPDF
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    def extract(self, pdf_path: Path) -> str:
        """Extract plain text from PDF."""
        try:
            doc = fitz.open(str(pdf_path))
            text_parts = []

            for page in doc:
                text_parts.append(page.get_text())

            doc.close()
            return "\n".join(text_parts).strip()
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise
