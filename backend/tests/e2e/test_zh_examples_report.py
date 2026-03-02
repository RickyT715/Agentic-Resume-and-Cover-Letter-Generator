"""
End-to-end test: Run 3 Chinese job descriptions through the v3 pipeline.

Mirrors test_5_examples_report.py but uses Chinese JDs with language="zh".

Usage:
    python -m tests.e2e.test_zh_examples_report
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

API_URL = "http://localhost:48765/api"
POLL_INTERVAL = 3
MAX_WAIT = 600

ZH_JOB_DESCRIPTIONS = [
    {
        "label": "后端工程师 (Backend)",
        "jd": """后端开发工程师

公司：字节跳动
地点：北京（混合办公）

岗位职责：
- 负责核心业务后端系统的设计与开发
- 构建高性能、高可用的微服务架构，支撑千万级日活用户
- 参与系统架构设计和技术方案评审
- 优化系统性能，提升服务稳定性

任职要求：
- 计算机相关专业本科及以上学历
- 3年以上后端开发经验
- 精通Python、Go或Java中的至少一种语言
- 熟悉分布式系统设计和微服务架构
- 熟练使用MySQL、Redis、Kafka等中间件
- 了解Docker、Kubernetes等容器化技术
- 良好的编码习惯和系统设计能力

加分项：
- 有大规模分布式系统开发经验
- 熟悉云原生技术栈（AWS/GCP/阿里云）
- 有开源项目贡献经验
- 熟悉监控系统（Prometheus、Grafana）

薪资范围：40K-60K/月
""",
    },
    {
        "label": "前端开发工程师 (Frontend)",
        "jd": """高级前端开发工程师

公司：腾讯
地点：深圳（现场办公）

我们正在寻找一位优秀的前端开发工程师，负责公司核心产品的Web端开发工作。

工作内容：
- 负责产品前端架构设计和核心模块开发
- 使用React/TypeScript构建高质量的交互式Web应用
- 优化前端性能（首屏加载、代码分割、懒加载）
- 确保跨浏览器兼容性和响应式设计
- 与设计团队和后端团队紧密协作

必备技能：
- 3年以上前端开发经验
- 精通React、TypeScript和现代CSS（Tailwind CSS、CSS Modules）
- 熟悉状态管理方案（Redux、Zustand）
- 了解前端测试框架（Jest、React Testing Library）
- 熟悉Git和敏捷开发流程
- 良好的沟通能力和团队协作精神

优先考虑：
- 有Next.js或Remix开发经验
- 熟悉前端动画库（Framer Motion）
- 有组件库或设计系统开发经验
- 了解GraphQL

薪资：35K-55K/月
""",
    },
    {
        "label": "数据科学家 (Data Scientist)",
        "jd": """高级数据科学家 - 机器学习方向

公司：阿里巴巴达摩院
地点：杭州（混合办公）

岗位概述：
加入我们的机器学习团队，构建驱动业务决策的预测模型。你将参与自然语言处理、推荐系统和时间序列预测等方向的研究与落地。

任职资格：
- 计算机科学、统计学或相关量化学科硕士及以上学历
- 4年以上数据科学或机器学习行业经验
- 精通Python，熟练使用scikit-learn、TensorFlow或PyTorch
- 有NLP相关经验（Transformer、BERT、大模型微调）
- 熟练掌握SQL，有大规模数据处理经验（Spark、Hadoop）
- 扎实的统计建模和A/B测试能力
- 有模型部署上线经验（MLflow、SageMaker或类似平台）

加分项：
- 有推荐系统开发经验
- 了解因果推断方法
- 发表过学术论文或会议论文
- 有大语言模型应用和RAG架构经验

薪资：50K-80K/月 + 奖金
""",
    },
]


async def create_task(client: httpx.AsyncClient, jd: str) -> dict:
    """Create a new task with Chinese language."""
    resp = await client.post(
        f"{API_URL}/tasks",
        json={
            "job_description": jd,
            "generate_cover_letter": True,
            "template_id": "classic",
            "language": "zh",
        },
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
        print(f"  [{task_id}] Status: {status} ... ({int(time.time() - start)}s elapsed)")
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


def format_duration(ms: int | float) -> str:
    if ms < 1000:
        return f"{int(ms)}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


async def run_single_example(client: httpx.AsyncClient, example: dict, index: int) -> dict:
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
        print("  Creating task (language=zh)...")
        task = await create_task(client, jd)
        task_id = task["id"]
        task_number = task["task_number"]
        print(f"  Task created: id={task_id}, number={task_number}")

        print("  Starting v3 pipeline...")
        await start_task_v3(client, task_id)
        print("  Pipeline started, polling for completion...")

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

        if final_task.get("resume_pdf_path"):
            print("  Fetching ATS evaluation...")
            ev = await get_evaluation(client, task_id)
            if ev:
                result["evaluation"] = ev
                result["ats_score"] = ev.get("combined_score", ev.get("ats_score", 0))
                print(f"  ATS Score: {result['ats_score']:.0%}")
            else:
                print("  No evaluation available")

        if final_task.get("error_message"):
            print(f"  ERROR: {final_task['error_message']}")

    except Exception as e:
        result["status"] = "error"
        result["error_message"] = str(e)
        result["total_time_ms"] = (time.time() - overall_start) * 1000
        print(f"  ERROR: {e}")

    return result


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run Chinese E2E test")
    parser.add_argument("--provider", default=None, help="Override default AI provider")
    parser.add_argument("--report-name", default="report_zh_examples", help="Base name for report files")
    args = parser.parse_args()

    provider_label = args.provider or "default"
    print("=" * 60)
    print(f"Resume Generator E2E Test - Chinese Pipeline (provider: {provider_label})")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(f"{API_URL}/templates")
            resp.raise_for_status()
            print(f"Server is running. Templates: {len(resp.json())}")
        except Exception as e:
            print(f"ERROR: Server not reachable at {API_URL}: {e}")
            sys.exit(1)

        if args.provider:
            print(f"Switching default provider to: {args.provider}")
            resp = await client.put(f"{API_URL}/settings", json={"default_provider": args.provider})
            resp.raise_for_status()

        results = []
        for i, example in enumerate(ZH_JOB_DESCRIPTIONS, 1):
            result = await run_single_example(client, example, i)
            results.append(result)
            print(f"\n  [Example {i} done]\n")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY (Chinese Pipeline)")
    print("=" * 60)
    for i, r in enumerate(results, 1):
        status_icon = "OK" if r["status"] == "completed" else "FAIL"
        ats = r.get("ats_score", "N/A")
        ats_str = f"{ats:.0%}" if isinstance(ats, (int, float)) else str(ats)
        print(f"  {i}. [{status_icon}] {r['label']} - {format_duration(r['total_time_ms'])} - ATS: {ats_str}")
        if r.get("error_message"):
            print(f"     Error: {r['error_message'][:200]}")
    total = sum(r["total_time_ms"] for r in results)
    print(f"\n  Total time: {format_duration(total)}")
    print("=" * 60)

    # Save JSON report
    json_path = Path(__file__).parent / f"{args.report_name}.json"
    json_results = [{k: v for k, v in r.items() if k != "response_files"} for r in results]
    json_path.write_text(json.dumps(json_results, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print(f"JSON data saved to: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
