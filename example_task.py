#!/usr/bin/env python3
"""
Example Task — Full End-to-End Demonstration
─────────────────────────────────────────────
Submits a complex analysis task to the running API server,
polls for completion, and prints the full structured report.

Usage:
    python example_task.py [--host http://localhost:8000] [--task "your task"]
"""

import argparse
import json
import sys
import time

import requests


def submit_and_wait(host: str, task: str, timeout: int = 300) -> dict:
    print(f"\n{'='*60}")
    print("  Autonomous Multi-Agent System — Example Run")
    print(f"{'='*60}\n")

    # ── Health check ───────────────────────────────────────────────────────
    try:
        h = requests.get(f"{host}/health", timeout=5)
        hd = h.json()
        print(f"✔ API healthy — active tasks: {hd.get('active_tasks', 0)}")
    except Exception as e:
        print(f"✗ API not reachable at {host}: {e}")
        sys.exit(1)

    # ── Submit task ────────────────────────────────────────────────────────
    print(f"\n📋 Task:\n   {task}\n")
    r = requests.post(f"{host}/task", json={"task": task})
    r.raise_for_status()
    task_id = r.json()["task_id"]
    print(f"✔ Task submitted — ID: {task_id}\n")

    # ── Poll status ────────────────────────────────────────────────────────
    start = time.time()
    last_step = ""
    step_emoji = {
        "PlannerAgent": "📐",
        "ResearchAgent": "🔍",
        "CoderAgent": "💻",
        "ExecutorAgent": "⚙️",
        "CriticAgent": "🔬",
        "ReporterAgent": "📄",
    }

    while time.time() - start < timeout:
        try:
            sr = requests.get(f"{host}/status/{task_id}").json()
            status = sr.get("workflow_status", "running")
            step = sr.get("current_step", "")
            retry = sr.get("retry_count", 0)

            if step != last_step and step:
                emoji = step_emoji.get(step, "▶")
                print(f"  {emoji}  {step}{'  [retry #'+str(retry)+']' if retry else ''}")
                last_step = step

            if sr.get("human_confirmation_needed"):
                print(f"\n⚠  HUMAN REVIEW REQUIRED")
                print(f"   {sr.get('human_confirmation_message', '')}")
                ans = input("\n   Proceed? [y/n]: ").strip().lower()
                action = "proceed" if ans == "y" else "abort"
                requests.post(
                    f"{host}/confirm/{task_id}",
                    json={"action": action, "feedback": "Approved by human reviewer"},
                )
                if action == "abort":
                    print("Task aborted.")
                    sys.exit(0)
                print("   Resuming workflow…")
                continue

            if status == "complete":
                print(f"\n✅ Workflow complete in {time.time()-start:.1f}s")
                break
            elif status == "failed":
                print(f"\n❌ Workflow failed: {sr.get('error', 'unknown error')}")
                break

        except Exception as e:
            print(f"  (poll error: {e})")

        time.sleep(3)

    else:
        print(f"\n⏰ Timeout after {timeout}s")
        sys.exit(1)

    # ── Fetch result ───────────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("FETCHING FINAL REPORT")
    print("─"*60 + "\n")

    rr = requests.get(f"{host}/result/{task_id}")
    if rr.status_code != 200:
        print(f"Result not available: {rr.status_code}")
        return {}

    result = rr.json()

    # Print report
    print(result.get("report", "(no report)"))

    # ── Metrics summary ────────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("METRICS SUMMARY")
    print("─"*60)
    tokens = result.get("token_usage", {})
    timings = result.get("step_timings", {})
    artifacts = result.get("artifacts", [])

    print(f"\nToken Usage:")
    for agent, count in tokens.items():
        print(f"  {agent:20s} {count:,} tokens")
    print(f"  {'TOTAL':20s} {sum(tokens.values()):,} tokens")

    print(f"\nStep Timings:")
    for agent, secs in timings.items():
        print(f"  {agent:20s} {secs:.2f}s")

    if artifacts:
        print(f"\nGenerated Artifacts ({len(artifacts)}):")
        for a in artifacts:
            print(f"  📁 {a}")

    sources = result.get("sources", [])
    if sources:
        print(f"\nResearch Sources ({len(sources)}):")
        for s in sources[:5]:
            print(f"  🔗 {s}")

    # ── System-wide metrics ────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("SYSTEM METRICS")
    print("─"*60)
    mr = requests.get(f"{host}/metrics").json()
    print(f"  Tasks total:        {mr['total_tasks']}")
    print(f"  Success rate:       {mr['task_success_rate']:.0%}")
    print(f"  Avg latency:        {mr['avg_latency_s']:.1f}s")
    print(f"  Total tokens used:  {mr['total_tokens_used']:,}")
    print(f"  Total retries:      {mr['total_retries']}")
    print()

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an example task")
    parser.add_argument("--host", default="http://localhost:8000", help="API base URL")
    parser.add_argument(
        "--task",
        default=(
            "Research global electric vehicle (EV) adoption trends from 2018 to 2024. "
            "Generate a synthetic dataset with regional EV sales, market share, and charging "
            "infrastructure data. Perform statistical analysis, create visualisations including "
            "time-series charts, regional comparisons, and correlation plots. Identify the top 3 "
            "growth markets and key adoption drivers. Produce a comprehensive structured report "
            "with executable Python code, charts, and actionable business insights."
        ),
        help="Task description",
    )
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    submit_and_wait(args.host, args.task, args.timeout)
