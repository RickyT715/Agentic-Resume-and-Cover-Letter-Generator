"""
End-to-end test: Run 5 real examples through the v3 pipeline and generate a detailed report.

Mimics a real user:
  1. Create task with a job description
  2. Start v3 pipeline
  3. Poll until completion
  4. Collect all metrics (timing, tokens, prompts, outputs)
  5. Generate a comprehensive markdown report

Usage:
    python -m tests.e2e.test_5_examples_report
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

API_URL = "http://localhost:48765/api"
POLL_INTERVAL = 3  # seconds between status checks
MAX_WAIT = 600  # max seconds to wait per task

# 5 diverse job descriptions for testing
JOB_DESCRIPTIONS = [
    {
        "label": "Software Engineer (Backend)",
        "jd": """Software Engineer - Backend

Company: TechVista Inc.
Location: San Francisco, CA (Hybrid)

About the Role:
We are looking for a Backend Software Engineer to join our platform team. You will design and build scalable microservices that power our real-time data processing pipeline serving 10M+ daily active users.

Requirements:
- 3+ years of backend development experience
- Strong proficiency in Python, Go, or Java
- Experience with distributed systems and microservices architecture
- Familiarity with PostgreSQL, Redis, and message queues (Kafka/RabbitMQ)
- Knowledge of RESTful API design and gRPC
- Experience with Docker, Kubernetes, and CI/CD pipelines
- Strong understanding of data structures and algorithms

Nice to Have:
- Experience with event-driven architecture
- Familiarity with AWS or GCP cloud services
- Contributions to open-source projects
- Experience with monitoring tools (Prometheus, Grafana, Datadog)

What We Offer:
- Competitive salary ($150K-$200K)
- Equity package
- Flexible work schedule
- Learning & development budget
""",
    },
    {
        "label": "Data Scientist (ML)",
        "jd": """Senior Data Scientist - Machine Learning

Company: DataDriven Analytics
Location: New York, NY (Remote-friendly)

Role Summary:
Join our ML team to build predictive models that drive business decisions for Fortune 500 clients. You'll work on NLP, recommendation systems, and time-series forecasting.

Qualifications:
- MS or PhD in Computer Science, Statistics, or related quantitative field
- 4+ years of industry experience in data science or machine learning
- Expert-level Python skills with scikit-learn, TensorFlow, or PyTorch
- Experience with NLP (transformers, BERT, GPT fine-tuning)
- Strong SQL skills and experience with large-scale data processing (Spark, Hadoop)
- Proficiency in statistical modeling and A/B testing
- Experience deploying ML models to production (MLflow, SageMaker, or similar)

Preferred:
- Experience with recommendation systems
- Knowledge of causal inference methods
- Published research or conference papers
- Experience with LLM applications and RAG architectures

Compensation: $170K-$220K base + bonus
""",
    },
    {
        "label": "Frontend Developer (React)",
        "jd": """Frontend Developer

Company: PixelCraft Design Studio
Location: Austin, TX (On-site)

We're looking for a talented Frontend Developer to create beautiful, responsive web applications for our agency clients spanning e-commerce, SaaS, and media industries.

What You'll Do:
- Build pixel-perfect UIs from Figma designs
- Develop interactive web applications using React and TypeScript
- Optimize performance (Core Web Vitals, lazy loading, code splitting)
- Implement responsive designs and ensure cross-browser compatibility
- Collaborate with designers and backend engineers

Must Have:
- 2+ years of professional frontend development
- Proficiency in React, TypeScript, and modern CSS (Tailwind CSS, CSS Modules)
- Experience with state management (Redux, Zustand, or React Context)
- Familiarity with testing frameworks (Jest, React Testing Library, Cypress)
- Understanding of web accessibility standards (WCAG 2.1)
- Experience with Git and agile development workflows

Bonus Points:
- Experience with Next.js or Remix
- Animation libraries (Framer Motion, GSAP)
- Design systems and component libraries (Storybook)
- GraphQL experience

Salary: $110K-$150K
""",
    },
    {
        "label": "DevOps Engineer",
        "jd": """DevOps / Site Reliability Engineer

Company: CloudScale Systems
Location: Seattle, WA (Hybrid)

About the Position:
We need a DevOps/SRE to maintain and scale our cloud infrastructure supporting a multi-region SaaS platform with 99.99% uptime requirements.

Key Responsibilities:
- Design and manage cloud infrastructure on AWS (EC2, ECS, Lambda, S3, RDS)
- Build and maintain CI/CD pipelines (GitHub Actions, Jenkins, ArgoCD)
- Implement Infrastructure as Code (Terraform, CloudFormation, Pulumi)
- Monitor system health with Prometheus, Grafana, PagerDuty, and ELK stack
- Manage Kubernetes clusters and containerized workloads
- Implement security best practices (IAM, VPC, secrets management)
- Automate operational tasks with Python and Bash scripting
- Participate in on-call rotation

Requirements:
- 3-5 years of DevOps/SRE experience
- Deep knowledge of AWS services
- Strong experience with Kubernetes and Docker
- Proficiency in Terraform or equivalent IaC tools
- Experience with Linux system administration
- Scripting skills in Python and/or Bash
- Understanding of networking concepts (DNS, load balancing, CDN)
- Experience with database management (PostgreSQL, DynamoDB)

Compensation: $140K-$185K + on-call bonus
""",
    },
    {
        "label": "Product Manager (Technical)",
        "jd": """Senior Technical Product Manager

Company: InnovateTech Solutions
Location: Chicago, IL (Remote)

Role Overview:
Lead the product strategy and roadmap for our developer tools platform. You'll work at the intersection of technology and business, translating customer needs into product features that delight developers.

What You'll Do:
- Define and prioritize product roadmap based on customer feedback and market analysis
- Write detailed PRDs and user stories with clear acceptance criteria
- Work closely with engineering teams to scope and deliver features
- Analyze product metrics and user behavior to inform decisions
- Conduct user research, competitive analysis, and market sizing
- Present product strategy to executive stakeholders
- Manage cross-functional relationships (Engineering, Design, Marketing, Sales)

Qualifications:
- 5+ years of product management experience, 2+ in developer tools or platforms
- Technical background (CS degree or prior engineering experience)
- Strong analytical skills with experience in data analysis tools (SQL, Amplitude, Mixpanel)
- Excellent written and verbal communication skills
- Experience with agile/scrum methodologies
- Track record of shipping successful products

Nice to Have:
- Experience with API products or developer ecosystems
- Understanding of cloud computing and SaaS business models
- MBA or equivalent business education
- Public speaking or content creation experience

Salary Range: $160K-$210K + equity
""",
    },
]


async def create_task(client: httpx.AsyncClient, jd: str) -> dict:
    """Create a new task with the given job description."""
    resp = await client.post(
        f"{API_URL}/tasks",
        json={
            "job_description": jd,
            "generate_cover_letter": True,
            "template_id": "classic",
            "language": "en",
        },
    )
    resp.raise_for_status()
    return resp.json()


async def start_task_v3(client: httpx.AsyncClient, task_id: str) -> dict:
    """Start the v3 pipeline for a task."""
    resp = await client.post(f"{API_URL}/tasks/{task_id}/start-v3")
    resp.raise_for_status()
    return resp.json()


async def poll_task(client: httpx.AsyncClient, task_id: str) -> dict:
    """Poll until task is completed, failed, or cancelled."""
    start = time.time()
    while time.time() - start < MAX_WAIT:
        resp = await client.get(f"{API_URL}/tasks/{task_id}")
        resp.raise_for_status()
        task = resp.json()
        status = task["status"]
        if status in ("completed", "failed", "cancelled"):
            return task
        print(f"  [{task_id}] Status: {status} ... ({int(time.time() - start)}s elapsed)")
        await asyncio.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Task {task_id} did not complete within {MAX_WAIT}s")


async def get_evaluation(client: httpx.AsyncClient, task_id: str) -> dict | None:
    """Fetch ATS evaluation for a task."""
    try:
        resp = await client.get(f"{API_URL}/tasks/{task_id}/evaluation")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def collect_response_files(task_number: int) -> list[dict]:
    """Read all response log files for a given task number."""
    responses_dir = Path(__file__).parent.parent.parent / "responses"
    files = sorted(responses_dir.glob(f"task_{task_number}_*.txt"))
    results = []
    for f in files:
        content = f.read_text(encoding="utf-8", errors="replace")
        # Parse sections
        entry = {"filename": f.name, "raw": content}

        # Extract prompt
        prompt_start = content.find("PROMPT\n" + "=" * 80)
        response_start = content.find("RESPONSE\n" + "=" * 80)
        if prompt_start >= 0 and response_start >= 0:
            prompt_section = content[prompt_start + len("PROMPT\n" + "=" * 80) : response_start]
            entry["prompt"] = prompt_section.strip()
            entry["prompt_chars"] = len(entry["prompt"])
        else:
            entry["prompt"] = ""
            entry["prompt_chars"] = 0

        # Extract response
        if response_start >= 0:
            end_marker = content.find("\n" + "=" * 80 + "\nEND OF LOG", response_start + 1)
            response_section = content[
                response_start + len("RESPONSE\n" + "=" * 80) : end_marker if end_marker >= 0 else None
            ]
            entry["response"] = response_section.strip()
            entry["response_chars"] = len(entry["response"])
        else:
            entry["response"] = ""
            entry["response_chars"] = 0

        # Extract metadata from header
        for line in content[:500].split("\n"):
            if "Response Type:" in line:
                entry["response_type"] = line.split(":", 1)[1].strip()
            if "Model:" in line:
                entry["model"] = line.split(":", 1)[1].strip()

        results.append(entry)
    return results


def format_duration(ms: int | float) -> str:
    """Format milliseconds to human-readable string."""
    if ms < 1000:
        return f"{int(ms)}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def generate_report(results: list[dict]) -> str:
    """Generate a comprehensive markdown report."""
    lines = []
    lines.append("# Resume Generator E2E Test Report")
    lines.append(f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("**Pipeline:** v3 (Multi-Agent LangGraph)")
    lines.append(f"**Examples Run:** {len(results)}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| # | Job Title | Status | Total Time | Input Tokens | Output Tokens | Total Tokens | ATS Score |")
    lines.append("|---|-----------|--------|------------|--------------|---------------|--------------|-----------|")

    grand_total_time = 0
    grand_total_input = 0
    grand_total_output = 0
    grand_total_tokens = 0

    for i, r in enumerate(results, 1):
        total_time = r.get("total_time_ms", 0)
        grand_total_time += total_time

        # Sum tokens across agents
        total_input = 0
        total_output = 0
        total_tok = 0
        for agent_name, agent_data in r.get("agent_outputs", {}).items():
            tu = agent_data.get("token_usage", {})
            total_input += tu.get("input_tokens", 0)
            total_output += tu.get("output_tokens", 0)
            total_tok += tu.get("total_tokens", 0)

        grand_total_input += total_input
        grand_total_output += total_output
        grand_total_tokens += total_tok

        ats = r.get("ats_score", "N/A")
        if isinstance(ats, (int, float)):
            ats = f"{ats:.0%}"

        lines.append(
            f"| {i} | {r['label']} | {r['status']} | {format_duration(total_time)} "
            f"| {total_input:,} | {total_output:,} | {total_tok:,} | {ats} |"
        )

    lines.append(
        f"| **Total** | | | **{format_duration(grand_total_time)}** "
        f"| **{grand_total_input:,}** | **{grand_total_output:,}** | **{grand_total_tokens:,}** | |"
    )
    lines.append("")

    # Detailed section per example
    for i, r in enumerate(results, 1):
        lines.append("---\n")
        lines.append(f"## Example {i}: {r['label']}")
        lines.append("")
        lines.append(f"**Status:** {r['status']}")
        lines.append(f"**Total Time:** {format_duration(r.get('total_time_ms', 0))}")
        if r.get("company_name"):
            lines.append(f"**Company:** {r['company_name']}")
        if r.get("position_name"):
            lines.append(f"**Position:** {r['position_name']}")
        lines.append("")

        # Job Description (truncated)
        lines.append("### Job Description")
        lines.append("```")
        jd_text = r.get("jd", "")
        if len(jd_text) > 800:
            lines.append(jd_text[:800] + "\n... (truncated)")
        else:
            lines.append(jd_text)
        lines.append("```")
        lines.append("")

        # Agent/Section breakdown
        lines.append("### Pipeline Breakdown (Per Agent)")
        lines.append("")
        lines.append("| Agent | Latency | Input Tokens | Output Tokens | Total Tokens | Extra Info |")
        lines.append("|-------|---------|-------------|---------------|--------------|------------|")

        agent_order = [
            "jd_analyzer",
            "relevance_matcher",
            "auto_company_research",
            "resume_writer",
            "compile_latex",
            "cover_letter_writer",
            "create_cover_pdf",
        ]
        agent_outputs = r.get("agent_outputs", {})
        for agent_name in agent_order:
            if agent_name not in agent_outputs:
                continue
            ad = agent_outputs[agent_name]
            latency = format_duration(ad.get("latency_ms", 0))
            tu = ad.get("token_usage", {})
            inp = tu.get("input_tokens", 0)
            out = tu.get("output_tokens", 0)
            tot = tu.get("total_tokens", 0)

            extra_parts = []
            if "match_score" in ad:
                extra_parts.append(f"match={ad['match_score']:.2f}")
            if "skills_found" in ad:
                extra_parts.append(f"skills={ad['skills_found']}")
            if "latex_length" in ad:
                extra_parts.append(f"latex={ad['latex_length']}ch")
            if "text_length" in ad:
                extra_parts.append(f"text={ad['text_length']}ch")
            if "attempt" in ad:
                extra_parts.append(f"attempt={ad['attempt']}")
            extra = ", ".join(extra_parts) or "-"

            lines.append(f"| {agent_name} | {latency} | {inp:,} | {out:,} | {tot:,} | {extra} |")
        lines.append("")

        # ATS Evaluation
        if r.get("evaluation"):
            ev = r["evaluation"]
            lines.append("### ATS Evaluation")
            lines.append(f"- **Combined Score:** {ev.get('combined_score', 0):.0%}")
            lines.append(f"- **ATS Score:** {ev.get('ats_score', 0):.0%}")
            lines.append(f"- **Passed:** {'Yes' if ev.get('passed') else 'No'}")
            bd = ev.get("ats_breakdown", {})
            if bd:
                lines.append(f"- Keyword Relevance: {bd.get('keyword_similarity', 0):.0%}")
                lines.append(f"- Semantic Match: {bd.get('semantic_similarity', 0):.0%}")
                lines.append(f"- Skill Coverage: {bd.get('skill_coverage', 0):.0%}")
                lines.append(f"- Fuzzy Match: {bd.get('fuzzy_match', 0):.0%}")
                lines.append(f"- Resume Quality: {bd.get('resume_quality', 0):.0%}")
            matched = ev.get("matched_keywords", [])
            missing = ev.get("missing_keywords", [])
            if matched:
                lines.append(f"- **Matched Keywords:** {', '.join(matched[:15])}")
            if missing:
                lines.append(f"- **Missing Keywords:** {', '.join(missing[:10])}")
            lines.append("")

        # LLM Calls detail (from response files)
        response_files = r.get("response_files", [])
        if response_files:
            lines.append("### LLM API Calls Detail")
            lines.append("")
            for j, rf in enumerate(response_files, 1):
                lines.append(f"#### Call {j}: {rf.get('response_type', 'unknown')} ({rf.get('model', 'unknown')})")
                lines.append(f"- **File:** `{rf['filename']}`")
                lines.append(f"- **Prompt Size:** {rf['prompt_chars']:,} chars")
                lines.append(f"- **Response Size:** {rf['response_chars']:,} chars")

                # Show prompt (truncated)
                lines.append("")
                lines.append("<details>")
                lines.append(f"<summary>Prompt ({rf['prompt_chars']:,} chars)</summary>")
                lines.append("")
                lines.append("```")
                prompt_text = rf.get("prompt", "")
                if len(prompt_text) > 2000:
                    lines.append(prompt_text[:2000] + "\n... (truncated)")
                else:
                    lines.append(prompt_text)
                lines.append("```")
                lines.append("</details>")
                lines.append("")

        # Resume LaTeX (truncated)
        if r.get("latex_source"):
            lines.append("### Generated Resume (LaTeX)")
            lines.append("<details>")
            lines.append("<summary>LaTeX source</summary>")
            lines.append("")
            lines.append("```latex")
            latex = r["latex_source"]
            if len(latex) > 3000:
                lines.append(latex[:3000] + "\n... (truncated)")
            else:
                lines.append(latex)
            lines.append("```")
            lines.append("</details>")
            lines.append("")

        # Error if any
        if r.get("error_message"):
            lines.append("### Error")
            lines.append(f"```\n{r['error_message']}\n```")
            lines.append("")

    return "\n".join(lines)


async def run_single_example(client: httpx.AsyncClient, example: dict, index: int) -> dict:
    """Run a single example end-to-end."""
    label = example["label"]
    jd = example["jd"]
    print(f"\n{'=' * 60}")
    print(f"Example {index}: {label}")
    print(f"{'=' * 60}")

    result = {
        "label": label,
        "jd": jd,
        "status": "unknown",
        "total_time_ms": 0,
    }

    overall_start = time.time()

    try:
        # Step 1: Create task
        print("  Creating task...")
        task = await create_task(client, jd)
        task_id = task["id"]
        task_number = task["task_number"]
        print(f"  Task created: id={task_id}, number={task_number}")

        # Step 2: Start v3 pipeline
        print("  Starting v3 pipeline...")
        await start_task_v3(client, task_id)
        print("  Pipeline started, polling for completion...")

        # Step 3: Poll until done
        final_task = await poll_task(client, task_id)
        total_ms = (time.time() - overall_start) * 1000

        result["status"] = final_task["status"]
        result["total_time_ms"] = total_ms
        result["company_name"] = final_task.get("company_name", "")
        result["position_name"] = final_task.get("position_name", "")
        result["latex_source"] = final_task.get("latex_source", "")
        result["error_message"] = final_task.get("error_message", "")
        result["agent_outputs"] = final_task.get("agent_outputs", {})
        result["task_id"] = task_id
        result["task_number"] = task_number

        print(f"  Status: {final_task['status']} in {format_duration(total_ms)}")

        # Step 4: Fetch evaluation
        if final_task.get("resume_pdf_path"):
            print("  Fetching ATS evaluation...")
            ev = await get_evaluation(client, task_id)
            if ev:
                result["evaluation"] = ev
                result["ats_score"] = ev.get("combined_score", ev.get("ats_score", 0))
                print(f"  ATS Score: {result['ats_score']:.0%}")
            else:
                print("  No evaluation available")

        # Step 5: Collect response files
        response_files = collect_response_files(task_number)
        result["response_files"] = response_files
        print(f"  Found {len(response_files)} response log files")

    except Exception as e:
        result["status"] = "error"
        result["error_message"] = str(e)
        result["total_time_ms"] = (time.time() - overall_start) * 1000
        print(f"  ERROR: {e}")

    return result


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run 5-example E2E test")
    parser.add_argument("--provider", default=None, help="Override default AI provider (gemini, claude_proxy, etc.)")
    parser.add_argument(
        "--report-name", default="report_5_examples", help="Base name for report files (e.g. report_5_examples_claude)"
    )
    args = parser.parse_args()

    provider_label = args.provider or "default"
    print("=" * 60)
    print(f"Resume Generator E2E Test - 5 Examples (provider: {provider_label})")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Verify server is running
        try:
            resp = await client.get(f"{API_URL}/templates")
            resp.raise_for_status()
            print(f"Server is running. Templates: {len(resp.json())}")
        except Exception as e:
            print(f"ERROR: Server not reachable at {API_URL}: {e}")
            sys.exit(1)

        # Switch provider if requested
        if args.provider:
            print(f"Switching default provider to: {args.provider}")
            resp = await client.put(
                f"{API_URL}/settings",
                json={"default_provider": args.provider},
            )
            resp.raise_for_status()
            settings = resp.json()
            print(f"  Confirmed provider: {settings.get('default_provider')}")

        # Run all 5 examples sequentially
        results = []
        for i, example in enumerate(JOB_DESCRIPTIONS, 1):
            result = await run_single_example(client, example, i)
            results.append(result)
            print(f"\n  [Example {i} done]\n")

    # Generate report
    print("\n" + "=" * 60)
    print("Generating report...")
    report = generate_report(results)

    # Save report
    report_path = Path(__file__).parent.parent.parent / "tests" / "e2e" / f"{args.report_name}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Report saved to: {report_path}")

    # Also save raw JSON data
    json_path = report_path.with_suffix(".json")
    # Remove raw content from JSON (too large)
    json_results = []
    for r in results:
        jr = {k: v for k, v in r.items() if k not in ("response_files",)}
        # Add summarized response files
        if r.get("response_files"):
            jr["response_files_summary"] = [
                {
                    "filename": rf["filename"],
                    "response_type": rf.get("response_type", ""),
                    "model": rf.get("model", ""),
                    "prompt_chars": rf["prompt_chars"],
                    "response_chars": rf["response_chars"],
                }
                for rf in r["response_files"]
            ]
        json_results.append(jr)

    json_path.write_text(json.dumps(json_results, indent=2, default=str), encoding="utf-8")
    print(f"JSON data saved to: {json_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for i, r in enumerate(results, 1):
        status_emoji = "OK" if r["status"] == "completed" else "FAIL"
        print(f"  {i}. [{status_emoji}] {r['label']} - {format_duration(r['total_time_ms'])}")
    total = sum(r["total_time_ms"] for r in results)
    print(f"\n  Total time: {format_duration(total)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
