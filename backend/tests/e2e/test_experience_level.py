"""
End-to-end test: Verify the experience_level feature works correctly.

Tests three scenarios:
  1. experience_level="new_grad"  - Should omit Summary, use Education-first ordering
  2. experience_level="experienced" - Should include Summary, use Experience-first ordering
  3. experience_level="auto" (default) - Baseline comparison

Requires a running server at localhost:48765.

Usage:
    python -m tests.e2e.test_experience_level
    python -m tests.e2e.test_experience_level --provider claude_proxy
"""

import asyncio
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

API_URL = "http://localhost:48765/api"
POLL_INTERVAL = 3
MAX_WAIT = 600

# A new-grad-appropriate JD (entry-level / intern)
NEW_GRAD_JD = """Software Engineer - New Grad / Entry Level

Company: CloudScale Technologies
Location: Seattle, WA (Hybrid)

About the Role:
We are looking for a motivated new graduate to join our engineering team. You will work on building and maintaining cloud-native applications, collaborating with senior engineers to deliver high-quality software.

Requirements:
- Bachelor's or Master's degree in Computer Science or related field (2024-2025 graduates)
- Strong foundation in data structures, algorithms, and object-oriented programming
- Proficiency in at least one programming language: Python, Java, or JavaScript/TypeScript
- Familiarity with web development (React, Node.js, or similar frameworks)
- Experience with Git version control
- Coursework or project experience with databases (SQL/NoSQL)
- Strong problem-solving skills and eagerness to learn

Nice to Have:
- Internship experience in software development
- Personal projects or open-source contributions on GitHub
- Familiarity with cloud services (AWS, GCP, or Azure)
- Knowledge of Docker and CI/CD concepts
- Experience with agile development methodologies

What We Offer:
- Competitive new grad salary ($95K-$120K)
- Mentorship program with senior engineers
- Education reimbursement
- Relocation assistance
"""

# An experienced-professional JD (5+ years)
EXPERIENCED_JD = """Senior Software Engineer - Backend Platform

Company: FinServe Global
Location: New York, NY (Remote OK)

About the Role:
We need a Senior Backend Engineer to lead the design and development of our core payment processing platform. You will architect scalable distributed systems handling millions of transactions daily and mentor a team of 4 engineers.

Requirements:
- 5+ years of professional software engineering experience
- Expert-level proficiency in Python and/or Go
- Deep experience with distributed systems, microservices, and event-driven architectures
- Strong knowledge of PostgreSQL, Redis, and Kafka
- Experience designing and operating systems at scale (1M+ TPS)
- Track record of leading technical projects and mentoring junior engineers
- Experience with AWS (ECS, Lambda, DynamoDB, SQS)
- Strong understanding of security best practices for financial systems

Nice to Have:
- Experience in fintech or payment processing
- Knowledge of compliance frameworks (PCI-DSS, SOC2)
- Experience with Kubernetes and infrastructure-as-code (Terraform)
- Contributions to system design or architecture documentation
- Experience with observability tools (Datadog, PagerDuty, Grafana)

Salary Range: $180K-$240K + equity + bonus
"""


def format_duration(ms: float) -> str:
    if ms < 1000:
        return f"{int(ms)}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


async def create_task(
    client: httpx.AsyncClient,
    jd: str,
    experience_level: str = "auto",
    language: str = "en",
) -> dict:
    resp = await client.post(
        f"{API_URL}/tasks",
        json={
            "job_description": jd,
            "generate_cover_letter": False,
            "template_id": "classic",
            "language": language,
            "experience_level": experience_level,
        },
    )
    resp.raise_for_status()
    return resp.json()


async def update_settings(
    client: httpx.AsyncClient,
    task_id: str,
    experience_level: str,
    jd: str,
) -> dict:
    resp = await client.put(
        f"{API_URL}/tasks/{task_id}/settings",
        json={"experience_level": experience_level, "job_description": jd},
    )
    resp.raise_for_status()
    return resp.json()


async def start_task_v3(client: httpx.AsyncClient, task_id: str) -> dict:
    resp = await client.post(f"{API_URL}/tasks/{task_id}/start-v3")
    resp.raise_for_status()
    return resp.json()


async def poll_task(client: httpx.AsyncClient, task_id: str) -> dict:
    start = time.time()
    while time.time() - start < MAX_WAIT:
        resp = await client.get(f"{API_URL}/tasks/{task_id}")
        resp.raise_for_status()
        task = resp.json()
        status = task["status"]
        if status in ("completed", "failed", "cancelled"):
            return task
        print(f"    [{task_id}] Status: {status} ... ({int(time.time() - start)}s)")
        await asyncio.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Task {task_id} did not complete within {MAX_WAIT}s")


async def get_evaluation(client: httpx.AsyncClient, task_id: str) -> dict | None:
    try:
        resp = await client.get(f"{API_URL}/tasks/{task_id}/evaluation")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def analyze_latex(latex: str) -> dict:
    """Analyze a LaTeX resume to check section ordering and content."""
    analysis = {
        "has_summary": False,
        "has_education": False,
        "has_experience": False,
        "has_skills": False,
        "has_projects": False,
        "sections_order": [],
        "section_positions": {},
    }

    # Find all \section{...} commands and their positions
    section_pattern = re.compile(r"\\section\{([^}]+)\}")
    for match in section_pattern.finditer(latex):
        section_name = match.group(1).strip()
        pos = match.start()
        analysis["section_positions"][section_name] = pos
        analysis["sections_order"].append(section_name)

        name_lower = section_name.lower()
        if "summary" in name_lower or "总结" in section_name:
            analysis["has_summary"] = True
        elif "education" in name_lower or "教育" in section_name:
            analysis["has_education"] = True
        elif "experience" in name_lower or "工作" in section_name or "经验" in section_name:
            analysis["has_experience"] = True
        elif "skill" in name_lower or "技能" in section_name:
            analysis["has_skills"] = True
        elif "project" in name_lower or "项目" in section_name:
            analysis["has_projects"] = True

    # Check for \resumeSummary command usage
    analysis["uses_resumeSummary_cmd"] = "\\resumeSummary{" in latex

    return analysis


async def run_scenario(
    client: httpx.AsyncClient,
    label: str,
    jd: str,
    experience_level: str,
    language: str = "en",
) -> dict:
    print(f"\n  {'─' * 50}")
    print(f"  Scenario: {label}")
    print(f"  experience_level={experience_level}, language={language}")
    print(f"  {'─' * 50}")

    result = {
        "label": label,
        "experience_level": experience_level,
        "language": language,
        "status": "unknown",
        "total_time_ms": 0,
        "checks": [],
    }

    overall_start = time.time()

    try:
        # Create task
        print("    Creating task...")
        task = await create_task(client, jd, experience_level=experience_level, language=language)
        task_id = task["id"]
        print(f"    Task created: id={task_id}, experience_level={task.get('experience_level')}")

        # Verify experience_level was stored
        if task.get("experience_level") == experience_level:
            result["checks"].append(("experience_level stored correctly", True))
        else:
            result["checks"].append((
                f"experience_level stored correctly (expected={experience_level}, got={task.get('experience_level')})",
                False,
            ))

        # Start v3 pipeline
        print("    Starting v3 pipeline...")
        await start_task_v3(client, task_id)
        print("    Pipeline started, polling...")

        # Poll
        final_task = await poll_task(client, task_id)
        total_ms = (time.time() - overall_start) * 1000

        result["status"] = final_task["status"]
        result["total_time_ms"] = total_ms
        result["company_name"] = final_task.get("company_name", "")
        result["position_name"] = final_task.get("position_name", "")
        result["latex_source"] = final_task.get("latex_source", "")
        result["error_message"] = final_task.get("error_message", "")
        result["agent_outputs"] = final_task.get("agent_outputs", {})

        print(f"    Status: {final_task['status']} in {format_duration(total_ms)}")

        if final_task["status"] != "completed":
            result["checks"].append(("task completed successfully", False))
            print(f"    ERROR: {final_task.get('error_message', 'unknown error')}")
            return result

        result["checks"].append(("task completed successfully", True))

        # Analyze LaTeX
        latex = final_task.get("latex_source", "")
        if not latex:
            result["checks"].append(("latex_source present", False))
            return result

        result["checks"].append(("latex_source present", True))
        analysis = analyze_latex(latex)
        result["latex_analysis"] = analysis
        print(f"    Sections found: {analysis['sections_order']}")
        print(f"    Has Summary: {analysis['has_summary']}")

        # Experience-level-specific checks
        if experience_level == "new_grad":
            # Should NOT have Summary
            if not analysis["has_summary"]:
                result["checks"].append(("new_grad: Summary section omitted", True))
            else:
                result["checks"].append(("new_grad: Summary section omitted (FOUND Summary)", False))

            # Education should come before Experience
            if analysis["has_education"] and analysis["has_experience"]:
                edu_pos = analysis["section_positions"].get("Education", analysis["section_positions"].get("教育背景", 999999))
                exp_pos = analysis["section_positions"].get("Experience", analysis["section_positions"].get("工作经验", 0))
                if edu_pos < exp_pos:
                    result["checks"].append(("new_grad: Education before Experience", True))
                else:
                    result["checks"].append(("new_grad: Education before Experience", False))

        elif experience_level == "experienced":
            # Should have Summary
            if analysis["has_summary"]:
                result["checks"].append(("experienced: Summary section present", True))
            else:
                result["checks"].append(("experienced: Summary section present (NOT FOUND)", False))

            # Experience should come before Education
            if analysis["has_education"] and analysis["has_experience"]:
                edu_pos = analysis["section_positions"].get("Education", analysis["section_positions"].get("教育背景", 0))
                exp_pos = analysis["section_positions"].get("Experience", analysis["section_positions"].get("工作经验", 999999))
                if exp_pos < edu_pos:
                    result["checks"].append(("experienced: Experience before Education", True))
                else:
                    result["checks"].append(("experienced: Experience before Education", False))

        # ATS evaluation
        if final_task.get("resume_pdf_path"):
            print("    Fetching ATS evaluation...")
            ev = await get_evaluation(client, task_id)
            if ev:
                result["evaluation"] = ev
                result["ats_score"] = ev.get("combined_score", ev.get("ats_score", 0))
                print(f"    ATS Score: {result['ats_score']:.0%}")

    except Exception as e:
        result["status"] = "error"
        result["error_message"] = str(e)
        result["total_time_ms"] = (time.time() - overall_start) * 1000
        result["checks"].append((f"no exception: {e}", False))
        print(f"    ERROR: {e}")

    return result


def generate_report(results: list[dict]) -> str:
    lines = []
    lines.append("# Experience Level E2E Test Report")
    lines.append(f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("**Pipeline:** v3 (Multi-Agent LangGraph)")
    lines.append(f"**Scenarios Run:** {len(results)}")
    lines.append("")

    # Summary table
    lines.append("## Results Summary")
    lines.append("")
    lines.append("| # | Scenario | Level | Status | Time | ATS Score | Checks |")
    lines.append("|---|----------|-------|--------|------|-----------|--------|")

    total_pass = 0
    total_fail = 0
    for i, r in enumerate(results, 1):
        passed = sum(1 for _, ok in r.get("checks", []) if ok)
        failed = sum(1 for _, ok in r.get("checks", []) if not ok)
        total_pass += passed
        total_fail += failed
        check_str = f"{passed}/{passed + failed}"
        ats = r.get("ats_score", "N/A")
        if isinstance(ats, (int, float)):
            ats = f"{ats:.0%}"
        status_icon = "PASS" if r["status"] == "completed" and failed == 0 else "FAIL"
        lines.append(
            f"| {i} | {r['label']} | {r['experience_level']} | {status_icon} "
            f"| {format_duration(r.get('total_time_ms', 0))} | {ats} | {check_str} |"
        )

    lines.append("")
    lines.append(f"**Total Checks:** {total_pass} passed, {total_fail} failed")
    lines.append("")

    # Detail per scenario
    for i, r in enumerate(results, 1):
        lines.append("---\n")
        lines.append(f"## Scenario {i}: {r['label']}")
        lines.append(f"- **Experience Level:** `{r['experience_level']}`")
        lines.append(f"- **Language:** `{r['language']}`")
        lines.append(f"- **Status:** {r['status']}")
        lines.append(f"- **Time:** {format_duration(r.get('total_time_ms', 0))}")
        if r.get("company_name"):
            lines.append(f"- **Company:** {r['company_name']}")
        if r.get("position_name"):
            lines.append(f"- **Position:** {r['position_name']}")
        lines.append("")

        # Checks
        lines.append("### Checks")
        for check_name, passed in r.get("checks", []):
            icon = "PASS" if passed else "FAIL"
            lines.append(f"- [{icon}] {check_name}")
        lines.append("")

        # LaTeX analysis
        analysis = r.get("latex_analysis", {})
        if analysis:
            lines.append("### LaTeX Analysis")
            lines.append(f"- **Sections order:** {' -> '.join(analysis.get('sections_order', []))}")
            lines.append(f"- **Has Summary:** {analysis.get('has_summary')}")
            lines.append(f"- **Has Education:** {analysis.get('has_education')}")
            lines.append(f"- **Has Experience:** {analysis.get('has_experience')}")
            lines.append(f"- **Has Skills:** {analysis.get('has_skills')}")
            lines.append(f"- **Has Projects:** {analysis.get('has_projects')}")
            lines.append(f"- **Uses \\resumeSummary cmd:** {analysis.get('uses_resumeSummary_cmd')}")
            lines.append("")

        # ATS
        if r.get("evaluation"):
            ev = r["evaluation"]
            lines.append("### ATS Evaluation")
            lines.append(f"- **Combined Score:** {ev.get('combined_score', 0):.0%}")
            bd = ev.get("ats_breakdown", {})
            if bd:
                lines.append(f"- Keyword Relevance: {bd.get('keyword_similarity', 0):.0%}")
                lines.append(f"- Skill Coverage: {bd.get('skill_coverage', 0):.0%}")
            matched = ev.get("matched_keywords", [])
            missing = ev.get("missing_keywords", [])
            if matched:
                lines.append(f"- **Matched Keywords ({len(matched)}):** {', '.join(matched[:20])}")
            if missing:
                lines.append(f"- **Missing Keywords ({len(missing)}):** {', '.join(missing[:15])}")
            lines.append("")

        # LaTeX source
        if r.get("latex_source"):
            lines.append("### Generated Resume (LaTeX)")
            lines.append("<details>")
            lines.append("<summary>LaTeX source</summary>")
            lines.append("")
            lines.append("```latex")
            latex = r["latex_source"]
            lines.append(latex[:4000] + ("\n... (truncated)" if len(latex) > 4000 else ""))
            lines.append("```")
            lines.append("</details>")
            lines.append("")

        if r.get("error_message"):
            lines.append(f"### Error\n```\n{r['error_message']}\n```\n")

    return "\n".join(lines)


SCENARIOS = [
    {
        "label": "New Grad (EN) - Entry-level JD",
        "jd": NEW_GRAD_JD,
        "experience_level": "new_grad",
        "language": "en",
    },
    {
        "label": "Experienced (EN) - Senior Backend JD",
        "jd": EXPERIENCED_JD,
        "experience_level": "experienced",
        "language": "en",
    },
    {
        "label": "Auto (EN) - Entry-level JD",
        "jd": NEW_GRAD_JD,
        "experience_level": "auto",
        "language": "en",
    },
]


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Experience Level E2E Test")
    parser.add_argument("--provider", default=None, help="Override default AI provider")
    parser.add_argument("--report-name", default="report_experience_level", help="Base name for report file")
    parser.add_argument("--include-zh", action="store_true", help="Include Chinese language scenarios")
    args = parser.parse_args()

    print("=" * 60)
    print("Experience Level E2E Test")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    scenarios = list(SCENARIOS)
    if args.include_zh:
        scenarios.append({
            "label": "New Grad (ZH) - Entry-level JD",
            "jd": NEW_GRAD_JD,
            "experience_level": "new_grad",
            "language": "zh",
        })

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check server
        try:
            resp = await client.get(f"{API_URL}/templates")
            resp.raise_for_status()
            print(f"Server is running. Templates: {len(resp.json())}")
        except Exception as e:
            print(f"ERROR: Server not reachable at {API_URL}: {e}")
            sys.exit(1)

        if args.provider:
            print(f"Switching provider to: {args.provider}")
            resp = await client.put(f"{API_URL}/settings", json={"default_provider": args.provider})
            resp.raise_for_status()

        results = []
        for i, scenario in enumerate(scenarios, 1):
            result = await run_scenario(
                client,
                label=scenario["label"],
                jd=scenario["jd"],
                experience_level=scenario["experience_level"],
                language=scenario.get("language", "en"),
            )
            results.append(result)
            print(f"\n  [Scenario {i}/{len(scenarios)} done]\n")

    # Generate report
    print("\n" + "=" * 60)
    print("Generating report...")
    report = generate_report(results)

    report_dir = Path(__file__).parent.parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"{args.report_name}_{timestamp}.md"
    report_file.write_text(report, encoding="utf-8")
    print(f"Report saved to: {report_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    all_passed = True
    for r in results:
        passed = sum(1 for _, ok in r.get("checks", []) if ok)
        failed = sum(1 for _, ok in r.get("checks", []) if not ok)
        icon = "PASS" if r["status"] == "completed" and failed == 0 else "FAIL"
        if failed > 0 or r["status"] != "completed":
            all_passed = False
        print(f"  [{icon}] {r['label']} (experience_level={r['experience_level']}) "
              f"- {r['status']} - checks: {passed}/{passed + failed} "
              f"- {format_duration(r.get('total_time_ms', 0))}")
        for check_name, check_ok in r.get("checks", []):
            icon2 = "  PASS" if check_ok else "  FAIL"
            print(f"    [{icon2}] {check_name}")

    print("=" * 60)
    if all_passed:
        print("ALL SCENARIOS PASSED")
    else:
        print("SOME SCENARIOS FAILED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
