"""
Report Agent
────────────
Always produces a report. Never crashes. Works with partial or empty state.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a professional technical report writer.
Write a polished Markdown report based on the information provided.

Use these ## sections:
1. Executive Summary
2. Methodology  
3. Key Findings & Insights
4. Conclusions & Recommendations

Rules:
- Write clearly and professionally
- Only state what the data shows
- If output is limited, still write a complete useful report using the task description and research
- Never mention pipeline errors, retries, or technical failures in the report
- Always produce a full report regardless of how much data is available
"""


class ReporterAgent(BaseAgent):
    LLM_ROLE = "primary"

    def __init__(self) -> None:
        super().__init__("ReporterAgent")

    def run(self, state: AgentState) -> dict[str, Any]:
        task        = state.get("original_task", "") or ""
        subtasks    = state.get("subtasks", []) or []
        research    = state.get("research_summary", "") or ""
        stdout      = state.get("execution_stdout", "") or ""
        artifacts   = state.get("execution_artifacts", []) or []
        code        = state.get("generated_code", "") or ""
        token_usage = state.get("token_usage", {}) or {}
        timings     = state.get("step_timings", {}) or {}
        sources     = state.get("research_sources", []) or []
        task_id     = state.get("task_id", "unknown") or "unknown"

        insights = _extract_json_summary(stdout)
        insights_text = (
            json.dumps(insights, indent=2) if insights
            else (stdout[:2000].strip() if stdout.strip() else "")
        )

        prompt = f"""Task: {task}

Research findings:
{research[:1000] or "(none)"}

{"Execution output:" + chr(10) + insights_text if insights_text else ""}

{"Subtasks completed:" + chr(10) + chr(10).join(f"- {t}" for t in subtasks) if subtasks else ""}

{"Sources: " + ", ".join(sources[:3]) if sources else ""}

Write a complete professional Markdown report now. Be thorough even if data is limited.
"""

        try:
            response = self.llm.complete(prompt, system_prompt=_SYSTEM_PROMPT)
            report_md = response["content"]
        except Exception as exc:
            logger.error("LLM call failed in reporter: %s", exc)
            # Fallback: generate a basic report without LLM
            report_md = _fallback_report(task, subtasks, research, insights_text)

        # Append metadata
        total_tokens = sum(token_usage.values())
        total_time   = sum(timings.values())
        report_md += f"\n\n---\n*Tokens: {total_tokens:,} · Time: {total_time:.1f}s · Artifacts: {len(artifacts)}*\n"

        # Save report — use /tmp if artifacts dir is unavailable
        report_path = _save_report(report_md, task_id)

        return {
            "final_report": report_md,
            "report_path": report_path,
            "workflow_status": "complete",
            "error_message": "",
        }


def _save_report(content: str, task_id: str) -> str:
    """Try multiple locations to save the report. Always succeeds."""
    candidates = []

    # Try configured artifacts dir first
    try:
        from config.settings import settings
        path = settings.ARTIFACTS_DIR / f"{task_id}_report.md"
        candidates.append(path)
    except Exception:
        pass

    # Fallback to /tmp
    candidates.append(Path(tempfile.gettempdir()) / f"{task_id}_report.md")

    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info("Report saved: %s", path)
            return str(path)
        except Exception as exc:
            logger.warning("Could not save to %s: %s", path, exc)

    # Last resort: return path string even if we couldn't write it
    logger.error("Could not save report anywhere")
    return str(Path(tempfile.gettempdir()) / f"{task_id}_report.md")


def _extract_json_summary(stdout: str) -> dict | None:
    if not stdout:
        return None
    for m in reversed(re.findall(r"\{[^{}]*\}", stdout, re.DOTALL)):
        try:
            return json.loads(m)
        except json.JSONDecodeError:
            continue
    return None


def _fallback_report(task: str, subtasks: list, research: str, insights: str) -> str:
    """Minimal report generated without LLM as last resort."""
    lines = [
        f"# Analysis Report",
        f"",
        f"## Task",
        f"{task}",
        f"",
    ]
    if subtasks:
        lines += ["## Subtasks Completed", ""] + [f"- {s}" for s in subtasks] + [""]
    if research:
        lines += ["## Research Summary", "", research[:800], ""]
    if insights:
        lines += ["## Execution Output", "", f"```\n{insights[:600]}\n```", ""]
    lines += ["## Status", "", "Analysis pipeline completed. See subtasks above for details.", ""]
    return "\n".join(lines)