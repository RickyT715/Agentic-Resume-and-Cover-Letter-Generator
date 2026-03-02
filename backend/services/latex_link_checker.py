"""
LaTeX Link Checker
Scans LaTeX source for \\href{URL}{TEXT} patterns and fixes LinkedIn/GitHub URLs
to match the user's configured profile URLs.
"""

import logging
import re

logger = logging.getLogger(__name__)


def fix_latex_links(latex_source: str, linkedin_url: str, github_url: str) -> str:
    """Fix LinkedIn and GitHub URLs in LaTeX \\href commands.

    Args:
        latex_source: The LaTeX source code to scan
        linkedin_url: The user's correct LinkedIn URL (empty to skip)
        github_url: The user's correct GitHub URL (empty to skip)

    Returns:
        LaTeX source with corrected URLs
    """
    if not linkedin_url and not github_url:
        return latex_source

    fixed = latex_source

    if linkedin_url:
        fixed = _fix_href_urls(fixed, "linkedin.com", linkedin_url)

    if github_url:
        fixed = _fix_href_urls(fixed, "github.com", github_url)

    return fixed


def _fix_href_urls(latex: str, domain: str, correct_url: str) -> str:
    """Fix all \\href commands whose URL contains the given domain.

    If the display text is also a URL containing the domain, fix that too.
    If the display text is a label (e.g. "LinkedIn"), leave it alone.
    """
    # Pattern: \href{URL}{TEXT} — capture URL and display text
    pattern = re.compile(r"\\href\{([^}]*)\}\{([^}]*)\}")

    def replacer(match: re.Match) -> str:
        href_url = match.group(1)
        display_text = match.group(2)

        if domain not in href_url.lower():
            return match.group(0)

        new_href = correct_url
        new_display = display_text

        # If display text also looks like a URL with the same domain, fix it too
        if domain in display_text.lower() and ("http" in display_text.lower() or display_text.startswith("www.")):
            new_display = correct_url

        if new_href != href_url or new_display != display_text:
            logger.info(f"Link checker: fixed {domain} href {href_url!r} -> {new_href!r}")

        return f"\\href{{{new_href}}}{{{new_display}}}"

    return pattern.sub(replacer, latex)
