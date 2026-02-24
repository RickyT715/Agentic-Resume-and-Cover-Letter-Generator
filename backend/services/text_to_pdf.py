from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from pathlib import Path
from config import settings
import logging

logger = logging.getLogger(__name__)


class TextToPDFConverter:
    """
    Convert plain text to PDF while preserving exact formatting.
    Headers, paragraphs, and sign-off are kept as-is from Gemini output.
    """

    def convert(self, text: str, output_path: Path) -> Path:
        """Convert plain text to formatted PDF preserving exact structure."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=72,  # 1 inch
            rightMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        styles = getSampleStyleSheet()

        # Body text style - preserves formatting
        body_style = ParagraphStyle(
            "BodyText",
            parent=styles["Normal"],
            fontName=settings.cover_letter_font,
            fontSize=settings.cover_letter_font_size,
            leading=settings.cover_letter_font_size * 1.4,
            spaceAfter=6,
            alignment=TA_LEFT,
        )

        # Header style for name/contact info
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Normal"],
            fontName=settings.cover_letter_font,
            fontSize=settings.cover_letter_font_size,
            leading=settings.cover_letter_font_size * 1.2,
            spaceAfter=2,
            alignment=TA_LEFT,
        )

        story = []

        # Split by double newlines to get paragraphs
        # This preserves the exact structure from Gemini
        paragraphs = text.split("\n\n")

        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue

            # Clean up the paragraph
            # Replace single newlines with <br/> for line breaks within paragraph
            cleaned = para.strip()

            # Check if this looks like a header section (first few lines with contact info)
            # or a sign-off section
            lines = cleaned.split("\n")

            if len(lines) > 1 and i < 2:
                # Header section - multiple short lines (name, email, phone, date)
                for line in lines:
                    if line.strip():
                        story.append(Paragraph(self._escape_html(line.strip()), header_style))
                story.append(Spacer(1, 0.2 * inch))
            elif cleaned.lower().startswith("dear ") or cleaned.lower().startswith("sincerely"):
                # Greeting or sign-off - single line
                for line in lines:
                    if line.strip():
                        story.append(Paragraph(self._escape_html(line.strip()), body_style))
                if cleaned.lower().startswith("sincerely"):
                    story.append(Spacer(1, 0.3 * inch))  # Space for signature
            else:
                # Regular paragraph - preserve internal line breaks
                formatted = "<br/>".join(
                    self._escape_html(line) for line in lines if line.strip()
                )
                story.append(Paragraph(formatted, body_style))
                story.append(Spacer(1, 0.15 * inch))

        doc.build(story)
        logger.info(f"Cover letter PDF created: {output_path}")
        return output_path

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters for ReportLab."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text
