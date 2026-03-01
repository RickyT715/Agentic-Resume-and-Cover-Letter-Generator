import logging
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from config import settings

logger = logging.getLogger(__name__)

# CJK font registration state
_cjk_font_registered = False
_cjk_font_name: str | None = None


def _is_cjk_text(text: str) -> bool:
    """Detect if text contains significant CJK characters."""
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk_count > len(text) * 0.05


def _register_cjk_font() -> str | None:
    """Try to register a CJK-capable font with ReportLab. Returns font name or None."""
    global _cjk_font_registered, _cjk_font_name
    if _cjk_font_registered:
        return _cjk_font_name

    _cjk_font_registered = True

    # Try reportlab's built-in CJK support first (UniGB-UCS2-H for Simplified Chinese)
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        _cjk_font_name = "STSong-Light"
        logger.info("Registered CJK font: STSong-Light (ReportLab CID font)")
        return _cjk_font_name
    except Exception as e:
        logger.debug(f"CID font registration failed: {e}")

    # Try system TTF fonts
    try:
        import platform

        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_paths: list[tuple[str, str]] = []

        if platform.system() == "Windows":
            windir = Path("C:/Windows/Fonts")
            font_paths = [
                ("SimSun", str(windir / "simsun.ttc")),
                ("SimHei", str(windir / "simhei.ttf")),
                ("MicrosoftYaHei", str(windir / "msyh.ttc")),
            ]
        elif platform.system() == "Linux":
            font_paths = [
                ("FandolSong", "/usr/share/fonts/opentype/fandol/FandolSong-Regular.otf"),
                ("NotoSansCJK", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                ("WenQuanYi", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
            ]
        elif platform.system() == "Darwin":
            font_paths = [
                ("STSongti", "/System/Library/Fonts/STSongti.ttc"),
                ("PingFang", "/System/Library/Fonts/PingFang.ttc"),
            ]

        for font_name, font_path in font_paths:
            if Path(font_path).exists():
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                _cjk_font_name = font_name
                logger.info(f"Registered CJK font: {font_name} from {font_path}")
                return _cjk_font_name

    except Exception as e:
        logger.warning(f"TTF font registration failed: {e}")

    logger.warning("No CJK font available — Chinese cover letters may have missing characters")
    return None


class TextToPDFConverter:
    """
    Convert plain text to PDF while preserving exact formatting.
    Headers, paragraphs, and sign-off are kept as-is from Gemini output.
    Supports CJK text with automatic font detection.
    """

    def convert(self, text: str, output_path: Path) -> Path:
        """Convert plain text to formatted PDF preserving exact structure."""
        is_cjk = _is_cjk_text(text)

        # Use A4 for Chinese, letter for English
        page_size = A4 if is_cjk else letter

        # Determine font
        if is_cjk:
            cjk_font = _register_cjk_font()
            font_name = cjk_font or settings.cover_letter_font_zh_fallback
        else:
            font_name = settings.cover_letter_font

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
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
            fontName=font_name,
            fontSize=settings.cover_letter_font_size,
            leading=settings.cover_letter_font_size * 1.4,
            spaceAfter=6,
            alignment=TA_LEFT,
        )

        # Header style for name/contact info
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Normal"],
            fontName=font_name,
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
            elif (
                cleaned.lower().startswith("dear ")
                or cleaned.lower().startswith("sincerely")
                or cleaned.startswith("尊敬的")
                or cleaned.startswith("此致")
                or cleaned.startswith("敬启")
            ):
                # Greeting or sign-off - single line (English or Chinese)
                for line in lines:
                    if line.strip():
                        story.append(Paragraph(self._escape_html(line.strip()), body_style))
                if cleaned.lower().startswith("sincerely") or cleaned.startswith("此致"):
                    story.append(Spacer(1, 0.3 * inch))  # Space for signature
            else:
                # Regular paragraph - preserve internal line breaks
                formatted = "<br/>".join(self._escape_html(line) for line in lines if line.strip())
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
