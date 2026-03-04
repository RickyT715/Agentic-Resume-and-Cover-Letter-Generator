"""
Resume Validator Service
Validates generated LaTeX resumes against user information.

Three independent, toggleable validation methods:
1. Contact Info Replacement - directly overwrite the LaTeX header with parsed user info
2. Text Checker - regex-verify contact info appears correctly in LaTeX
3. LLM Checker - send LaTeX + user info to an LLM for full validation
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContactInfo:
    """Parsed contact information from user_information prompt text."""

    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""


def _escape_latex(text: str) -> str:
    """Escape LaTeX special characters in plain text for safe insertion."""
    replacements = [
        ("\\", "\\textbackslash{}"),
        ("#", "\\#"),
        ("$", "\\$"),
        ("%", "\\%"),
        ("&", "\\&"),
        ("_", "\\_"),
        ("{", "\\{"),
        ("}", "\\}"),
        ("~", "\\textasciitilde{}"),
        ("^", "\\textasciicircum{}"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)
    return text


def parse_contact_info(user_info_text: str, language: str = "en") -> ContactInfo:
    """Extract contact fields from the raw user information text.

    Args:
        user_info_text: The user_information prompt content
        language: "en" or "zh"

    Returns:
        ContactInfo with extracted fields
    """
    info = ContactInfo()
    if not user_info_text.strip():
        return info

    lines = user_info_text.strip().splitlines()

    # Name: try explicit "Name:" field first, then fall back to first non-header line
    if language == "zh":
        name_match = re.search(r"姓名[：:]\s*(.+)", user_info_text)
    else:
        name_match = re.search(r"Name\s*:\s*(.+)", user_info_text, re.IGNORECASE)
    if name_match:
        info.name = name_match.group(1).strip()
    else:
        # Fall back to first non-empty, non-markdown-header line
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                info.name = stripped
                break

    # Email
    if language == "zh":
        email_match = re.search(r"邮箱[：:]\s*(\S+)", user_info_text)
    else:
        email_match = re.search(r"Email\s*:\s*(\S+)", user_info_text, re.IGNORECASE)
    if not email_match:
        # Fallback: find any email-looking string
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", user_info_text)
    if email_match:
        info.email = email_match.group(1) if email_match.lastindex else email_match.group(0)

    # Phone
    if language == "zh":
        phone_match = re.search(r"电话[：:]\s*(\+?[\d\s\-()]+)", user_info_text)
    else:
        phone_match = re.search(r"Mobile\s*:\s*(\+?[\d\s\-()]+)", user_info_text, re.IGNORECASE)
    if not phone_match:
        phone_match = re.search(r"Phone\s*:\s*(\+?[\d\s\-()]+)", user_info_text, re.IGNORECASE)
    if phone_match:
        info.phone = phone_match.group(1).strip()

    # LinkedIn & GitHub: look for URLs in lines
    for line in lines:
        lower = line.strip().lower()
        if "linkedin.com" in lower:
            url_match = re.search(r"https?://[^\s,}]*linkedin\.com[^\s,}]*", line, re.IGNORECASE)
            if url_match:
                info.linkedin = url_match.group(0).rstrip(".")
            elif not info.linkedin:
                # Line itself might be the URL
                cleaned = line.strip().rstrip(".")
                if "linkedin.com" in cleaned.lower():
                    info.linkedin = cleaned
        if "github.com" in lower:
            url_match = re.search(r"https?://[^\s,}]*github\.com[^\s,}]*", line, re.IGNORECASE)
            if url_match:
                info.github = url_match.group(0).rstrip(".")
            elif not info.github:
                cleaned = line.strip().rstrip(".")
                if "github.com" in cleaned.lower():
                    info.github = cleaned

    return info


def replace_contact_header(latex: str, contact: ContactInfo) -> str:
    """Method 1: Replace the first tabular* contact header block with correct info.

    Finds the first \\begin{tabular*}{\\textwidth} ... \\end{tabular*} block
    and rebuilds it with correct values from ContactInfo.

    Args:
        latex: LaTeX source code
        contact: Parsed contact information

    Returns:
        Modified LaTeX with corrected header
    """
    if not contact.name:
        logger.warning("No name found in contact info, skipping header replacement")
        return latex

    # Find the first tabular* block (the contact header)
    pattern = re.compile(
        r"\\begin\{tabular\*\}\{\\textwidth\}.*?\\end\{tabular\*\}",
        re.DOTALL,
    )
    match = pattern.search(latex)
    if not match:
        logger.warning("No tabular* contact header found in LaTeX")
        return latex

    # Build replacement header — escape LaTeX special chars in user-provided text
    linkedin_url = contact.linkedin or ""
    safe_name = _escape_latex(contact.name)
    name_href = f"\\href{{{linkedin_url}}}{{\\Large {safe_name}}}" if linkedin_url else f"\\Large {safe_name}"

    email_part = ""
    if contact.email:
        safe_email = _escape_latex(contact.email)
        email_part = f"Email : \\href{{mailto:{contact.email}}}{{{safe_email}}}"

    phone_part = ""
    if contact.phone:
        safe_phone = _escape_latex(contact.phone)
        phone_part = f"Mobile : {safe_phone}"

    # Build rows
    rows = []
    # Row 1: Name (left) & Email (right)
    left_1 = f"  \\textbf{{{name_href}}}"
    right_1 = email_part
    rows.append(f"{left_1} & {right_1}\\\\")

    # Row 2: LinkedIn (left) & Phone (right)
    left_2 = f"  \\href{{{linkedin_url}}}{{{linkedin_url}}}" if linkedin_url else "  "
    right_2 = phone_part
    rows.append(f"{left_2} & {right_2} \\\\")

    # Row 3: GitHub (if available)
    if contact.github:
        left_3 = f"  \\href{{{contact.github}}}{{{contact.github}}}"
        rows.append(f"{left_3} & \\\\")

    rows_str = "\n".join(rows)
    replacement = f"\\begin{{tabular*}}{{\\textwidth}}{{l@{{\\extracolsep{{\\fill}}}}r}}\n{rows_str}\n\\end{{tabular*}}"

    result = latex[: match.start()] + replacement + latex[match.end() :]
    logger.info("Replaced contact header with parsed user info")
    return result


def check_contact_info(latex: str, contact: ContactInfo) -> list[str]:
    """Method 2: Verify that contact info appears correctly in the LaTeX.

    Args:
        latex: LaTeX source code
        contact: Parsed contact information

    Returns:
        List of warning strings (empty = all good)
    """
    warnings = []

    # Check each field
    if contact.name and contact.name not in latex:
        warnings.append(f"Name '{contact.name}' not found in resume")

    if contact.email and contact.email not in latex:
        warnings.append(f"Email '{contact.email}' not found in resume")

    if contact.phone:
        # Phone might have formatting differences — strip spaces/dashes for comparison
        phone_digits = re.sub(r"[\s\-()]", "", contact.phone)
        latex_digits = re.sub(r"[\s\-()]", "", latex)
        if phone_digits not in latex_digits:
            warnings.append(f"Phone '{contact.phone}' not found in resume")

    if contact.linkedin and contact.linkedin not in latex:
        warnings.append("LinkedIn URL not found in resume")

    if contact.github and contact.github not in latex:
        warnings.append("GitHub URL not found in resume")

    # Check for leftover placeholders
    placeholders = [
        "CANDIDATE_NAME",
        "CANDIDATE_EMAIL",
        "CANDIDATE_PHONE",
        "CANDIDATE_LINKEDIN",
        "CANDIDATE_GITHUB",
        "YOUR_NAME",
        "YOUR_EMAIL",
        "YOUR_PHONE",
        "PLACEHOLDER",
    ]
    for placeholder in placeholders:
        if placeholder in latex:
            warnings.append(f"Placeholder text '{placeholder}' still present in resume")

    return warnings


LLM_VALIDATION_PROMPT_EN = """You are a resume quality validator. Review this LaTeX resume against the candidate's information and job description.

## Candidate Information
{user_info}

## Job Description
{job_description}

## LaTeX Resume Source
```latex
{latex}
```

## Validation Checklist
Check ALL of the following and report ONLY actual issues found:

1. **Contact Info**: Does the resume header contain the EXACT name, email, phone, LinkedIn, and GitHub from the candidate information? Report any mismatches or missing fields.

2. **Required Sections**: Are all expected sections present (Education, Experience, Skills, Projects)? Report missing sections.

3. **Placeholder Text**: Is there any leftover placeholder text like "CANDIDATE_NAME", "YOUR_EMAIL", "Company XYZ", "20XX", etc.?

4. **Fabricated Content**: Are there company names, job titles, degrees, or institutions that do NOT appear in the candidate's information? (Note: skill rephrasing and emphasis is acceptable, but entirely invented employers or degrees are not.)

5. **LaTeX Issues**: Are there obviously mismatched braces, unclosed environments, or syntax errors that would prevent compilation?

## Response Format
If there are issues, respond with one issue per line, prefixed with "- ". Be specific and concise.
If everything looks correct, respond with exactly: NO_ISSUES_FOUND

Example:
- Name in header is "John Smith" but candidate info says "Jane Smith"
- Education section is missing
- Placeholder "Company XYZ" found in experience section
"""

LLM_VALIDATION_PROMPT_ZH = """你是一个简历质量验证器。请对照候选人信息和职位描述审查这份LaTeX简历。

## 候选人信息
{user_info}

## 职位描述
{job_description}

## LaTeX简历源码
```latex
{latex}
```

## 验证清单
检查以下所有项目，仅报告发现的实际问题：

1. **联系信息**：简历头部是否包含候选人信息中的准确姓名、邮箱、电话、LinkedIn和GitHub？报告任何不匹配或缺失的字段。

2. **必要板块**：是否包含所有必要板块（教育背景、工作经历、技能、项目）？报告缺失的板块。

3. **占位符文本**：是否有残留的占位符文本，如"候选人姓名"、"YOUR_EMAIL"、"XX公司"、"20XX"等？

4. **虚构内容**：是否有候选人信息中不存在的公司名、职位、学历或机构？（注意：技能重新措辞和强调是可以接受的，但完全虚构的雇主或学历不可接受。）

5. **LaTeX问题**：是否有明显的大括号不匹配、未关闭的环境或会阻止编译的语法错误？

## 回复格式
如有问题，每行一个问题，以"- "开头。请具体且简洁。
如果一切正确，请回复：NO_ISSUES_FOUND
"""


async def llm_validate_resume(
    latex: str,
    user_info_text: str,
    job_description: str,
    ai_client,
    language: str = "en",
) -> list[str]:
    """Method 3: Use an LLM to validate the entire resume.

    Args:
        latex: LaTeX source code
        user_info_text: Raw user information text
        job_description: The job description
        ai_client: AI provider client with a generate method
        language: "en" or "zh"

    Returns:
        List of warning strings (empty = all good)
    """
    template = LLM_VALIDATION_PROMPT_ZH if language == "zh" else LLM_VALIDATION_PROMPT_EN
    prompt = template.format(
        user_info=user_info_text[:3000],
        job_description=job_description[:3000],
        latex=latex[:8000],
    )

    try:
        response = await ai_client.generate(
            prompt,
            task_id="validation",
            task_number=0,
            response_type="resume_validation",
        )

        response_text = response.strip()
        if "NO_ISSUES_FOUND" in response_text:
            logger.info("LLM validation: no issues found")
            return []

        # Parse issues from response
        warnings = []
        for line in response_text.splitlines():
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                warnings.append(line[2:].strip())

        if not warnings and response_text:
            # LLM didn't follow format - treat whole response as one warning
            warnings.append(response_text[:500])

        logger.info(f"LLM validation: found {len(warnings)} issues")
        return warnings

    except Exception as e:
        logger.error(f"LLM validation failed: {e}")
        return [f"LLM validation failed: {e}"]


async def validate_resume_async(
    latex: str,
    user_info_text: str,
    language: str,
    settings_manager,
    ai_client=None,
    job_description: str = "",
    skip_llm: bool = False,
) -> tuple[str, list[str]]:
    """Async orchestrator: run enabled validation methods in order.

    Same as validate_resume but handles LLM validation natively.
    """
    enable_replacement = settings_manager.get("enable_contact_replacement", True)
    enable_text_check = settings_manager.get("enable_text_validation", True)
    enable_llm_check = settings_manager.get("enable_llm_validation", False)

    contact = parse_contact_info(user_info_text, language)
    warnings: list[str] = []
    current_latex = latex

    # Method 1: Replace contact header
    if enable_replacement:
        try:
            current_latex = replace_contact_header(current_latex, contact)
        except Exception as e:
            logger.error(f"Contact replacement failed: {e}")
            warnings.append(f"Contact header replacement failed: {e}")

    # Method 2: Text validation
    if enable_text_check:
        try:
            text_warnings = check_contact_info(current_latex, contact)
            warnings.extend(text_warnings)
        except Exception as e:
            logger.error(f"Text validation failed: {e}")
            warnings.append(f"Text validation error: {e}")

    # Method 3: LLM validation
    if enable_llm_check and not skip_llm and ai_client is not None:
        try:
            llm_warnings = await llm_validate_resume(
                current_latex, user_info_text, job_description, ai_client, language
            )
            warnings.extend(llm_warnings)
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            warnings.append(f"LLM validation error: {e}")

    return current_latex, warnings
