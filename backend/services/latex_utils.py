"""
LaTeX Utilities
Functions for extracting and post-processing LaTeX code from LLM responses.
"""

import logging
import re

logger = logging.getLogger(__name__)


def extract_metadata(response: str) -> dict:
    """
    Extract metadata comments (company name, position) from the raw LLM response.

    Looks for lines like:
        % META_COMPANY: Google
        % META_POSITION: Software Engineer
    in the text before \\documentclass.

    Returns dict with 'company_name' and 'position_name' (empty string if not found).
    """
    metadata = {"company_name": "", "position_name": ""}

    # Get text before \documentclass (where metadata comments live)
    doc_idx = response.find("\\documentclass")
    if doc_idx == -1:
        return metadata

    preamble = response[:doc_idx]

    company_match = re.search(r"%\s*META_COMPANY:\s*(.+)", preamble)
    if company_match:
        metadata["company_name"] = company_match.group(1).strip()

    position_match = re.search(r"%\s*META_POSITION:\s*(.+)", preamble)
    if position_match:
        metadata["position_name"] = position_match.group(1).strip()

    if metadata["company_name"] or metadata["position_name"]:
        logger.info(f"Extracted metadata: company={metadata['company_name']!r}, position={metadata['position_name']!r}")

    return metadata


def extract_latex(response: str) -> str:
    """
    Extract LaTeX code from response, handling markdown code blocks.

    Ensures we only get content from \\documentclass to \\end{document},
    removing any markdown formatting or extra text.
    """
    logger.debug("Extracting LaTeX from response")
    logger.debug(f"Response length: {len(response)} characters")

    text = response

    # Step 1: If wrapped in markdown code blocks, extract the inner content first
    # Pattern to match ```latex ... ``` or ``` ... ```
    pattern = r"```(?:latex)?\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL)

    if match:
        logger.debug("Found markdown code block, extracting inner content")
        text = match.group(1).strip()

    # Step 2: Now extract exactly from \documentclass to \end{document}
    # This ensures we get only valid LaTeX content
    if "\\documentclass" not in text:
        logger.error("Response does not contain \\documentclass")
        raise ValueError("Response does not contain valid LaTeX code (missing \\documentclass)")

    if "\\end{document}" not in text:
        logger.error("Response does not contain \\end{document}")
        raise ValueError("Response does not contain valid LaTeX code (missing \\end{document})")

    # Find the start: \documentclass
    start_idx = text.find("\\documentclass")

    # Find the end: \end{document} (last occurrence to be safe)
    end_idx = text.rfind("\\end{document}")
    end_idx += len("\\end{document}")

    # Extract only the LaTeX content
    latex_code = text[start_idx:end_idx].strip()

    logger.debug(f"Extracted LaTeX from index {start_idx} to {end_idx}")
    logger.debug(f"LaTeX starts with: {latex_code[:50]}...")
    logger.debug(f"LaTeX ends with: ...{latex_code[-50:]}")

    # Validate the extraction
    if not latex_code.startswith("\\documentclass"):
        logger.error("Extracted LaTeX does not start with \\documentclass")
        raise ValueError("LaTeX extraction failed - invalid start")

    if not latex_code.endswith("\\end{document}"):
        logger.error("Extracted LaTeX does not end with \\end{document}")
        raise ValueError("LaTeX extraction failed - invalid end")

    logger.info(f"Successfully extracted LaTeX code ({len(latex_code)} characters)")
    return latex_code


def post_process_latex(latex_code: str) -> str:
    """
    Apply post-processing fixes to the LaTeX code.

    Fixes:
    1. Change font size from 11pt to 10pt for better fit on one page
    2. Fix common LaTeX syntax errors from LLM output
    3. Fix special characters that break compilation
    """
    logger.debug("Applying post-processing fixes to LaTeX")

    # Fix 1: Change 11pt to 10pt for better page fit
    latex_code = re.sub(r"\\documentclass\[letterpaper,\s*11pt\]", r"\\documentclass[letterpaper,10pt]", latex_code)
    logger.debug("Changed font size from 11pt to 10pt")

    # Fix 2: Fix common \labelitemii syntax error
    # Wrong: \renewcommand{\labelitemii}{{\circ$}}
    # Wrong: \renewcommand{\labelitemii}{{$\circ}}
    # Correct: \renewcommand{\labelitemii}{$\circ$}
    latex_code = re.sub(
        r"\\renewcommand\{\\labelitemii\}\s*\{\s*\{?\s*\\circ\s*\$\s*\}?\s*\}",
        r"\\renewcommand{\\labelitemii}{$\\circ$}",
        latex_code,
    )
    latex_code = re.sub(
        r"\\renewcommand\{\\labelitemii\}\s*\{\s*\{?\s*\$\s*\\circ\s*\}?\s*\}",
        r"\\renewcommand{\\labelitemii}{$\\circ$}",
        latex_code,
    )
    # Also handle double braces variation
    latex_code = re.sub(
        r"\\renewcommand\{\\labelitemii\}\s*\{\s*\{\s*\$?\\circ\$?\s*\}\s*\}",
        r"\\renewcommand{\\labelitemii}{$\\circ$}",
        latex_code,
    )
    logger.debug("Fixed labelitemii syntax if present")

    # Fix 3: Fix < and > characters in text mode
    # These need to be wrapped in math mode: $<$ and $>$

    # Fix standalone < followed by numbers/text (like <1s, <100ms)
    latex_code = re.sub(r"(?<!\\)(?<!\$)<(\d)", r"$<$\1", latex_code)

    # Fix standalone > followed by numbers/text (like >50%, >100)
    latex_code = re.sub(r"(?<!\\)(?<!\$)>(\d)", r"$>$\1", latex_code)

    # Fix < or > between spaces or at word boundaries
    latex_code = re.sub(r"\s<\s", r" $<$ ", latex_code)
    latex_code = re.sub(r"\s>\s", r" $>$ ", latex_code)

    logger.debug("Fixed < and > characters")

    # Fix 4: Fix potential issues with empty href
    latex_code = re.sub(r"\\href\{\}\{", r"\\textbf{", latex_code)
    logger.debug("Fixed empty href if present")

    # Fix 5: Fix potential double dollar signs
    latex_code = latex_code.replace("$$\\circ$$", "$\\circ$")
    latex_code = latex_code.replace("$$<$$", "$<$")
    latex_code = latex_code.replace("$$>$$", "$>$")

    # Fix 6: Fix unescaped # character (common in LLM output)
    latex_code = re.sub(
        r"(?<!\\)#(?!\d)",  # # not preceded by \ and not followed by digit (param)
        r"\\#",
        latex_code,
    )

    # Fix 7: Fix unescaped & character (but not in tabular column specs)
    latex_code = re.sub(r"(\w)&(\w)", r"\1\\&\2", latex_code)

    # Fix 8: Remove any trailing/leading whitespace issues
    lines = latex_code.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    latex_code = "\n".join(lines)

    logger.info("Post-processing completed")
    return latex_code


def process_latex_response(response: str) -> str:
    """
    Extract and post-process LaTeX from a response.

    Combines extraction and post-processing in one call.

    Args:
        response: Raw response from LLM containing LaTeX code

    Returns:
        Cleaned and processed LaTeX code
    """
    latex_code = extract_latex(response)
    latex_code = post_process_latex(latex_code)
    return latex_code
