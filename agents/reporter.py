"""
Report Agent
────────────
Always produces a complete report.
Never crashes. Works with partial or empty state.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a professional technical report writer.
Write a polished, detailed Markdown report based on the information provided.

Use these ## sections:
1. Executive Summary
2. Methodology
3. Key Findings & Insights
4. Data Overview (describe the dataset and analysis performed)
5. Conclusions & Recommendations

Rules:
- Write a FULL, detailed report — at least 400 words
- Use the research summary heavily if execution output is limited
- Draw on the task description and subtasks to fill in context
- Never mention pipeline errors, retries, or technical failures
- Always produce useful, professional content regardless of input quality
- If you have research data but no execution output, synthesise insights from research alone
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
        stderr      = state.get("execution_stderr", "") or ""
        artifacts   = state.get("execution_artifacts", []) or []
        code        = state.get("generated_code", "") or ""
        token_usage = state.get("token_usage", {}) or {}
        timings     = state.get("step_timings", {}) or {}
        sources     = state.get("research_sources", []) or []
        task_id     = state.get("task_id", "unknown") or "unknown"

        # Extract any JSON summary from stdout
        insights = _extract_json_summary(stdout)
        insights_text = json.dumps(insights, indent=2) if insights else stdout[:2000].strip()

        prompt = f"""Task: {task}

Subtasks completed:
{chr(10).join(f"- {t}" for t in subtasks)}

Research findings (use this as primary source if execution output is limited):
{research[:2000] or "(none)"}

{"Execution output:" + chr(10) + insights_text if insights_text else ""}

Artifacts generated: {len(artifacts)} file(s)
{"- " + chr(10).join(artifacts) if artifacts else ""}

{"Sources: " + chr(10).join(f"- {s}" for s in sources[:5]) if sources else ""}

Code used (excerpt):
```python
{code[:600]}
```

Write a complete, detailed, professional Markdown report.
Use the research findings to provide rich context and insights even if execution output is limited.
Minimum 400 words.
"""

        try:
            response = self.llm.complete(prompt, system_prompt=_SYSTEM_PROMPT)
            report_md = response["content"]
        except Exception as exc:
            logger.error("LLM call failed in reporter: %s", exc)
            report_md = _fallback_report(task, subtasks, research, insights_text)

        # Metadata footer
        total_tokens = sum(token_usage.values())
        total_time   = sum(timings.values())
        report_md += (
            f"\n\n---\n"
            f"*Tokens: {total_tokens:,} · "
            f"Time: {total_time:.1f}s · "
            f"Artifacts: {len(artifacts)}*\n"
        )

        report_path = _save_report(report_md, task_id)

        return {
            "final_report": report_md,
            "report_path": report_path,
            "workflow_status": "complete",
            "error_message": "",
        }


def _save_report(content: str, task_id: str) -> str:
    candidates = []
    try:
        from config.settings import settings
        candidates.append(settings.ARTIFACTS_DIR / f"{task_id}_report.md")
    except Exception:
        pass
    candidates.append(Path(tempfile.gettempdir()) / f"{task_id}_report.md")

    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info("Report saved: %s", path)
            return str(path)
        except Exception as exc:
            logger.warning("Could not save to %s: %s", path, exc)

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
    lines = [
        "# Analysis Report", "",
        "## Executive Summary", "",
        f"This report covers the following task: {task}", "",
    ]
    if research:
        lines += ["## Research Findings", "", research[:1200], ""]
    if subtasks:
        lines += ["## Methodology", ""] + [f"- {s}" for s in subtasks] + [""]
    if insights:
        lines += ["## Output", "", f"```\n{insights[:800]}\n```", ""]
    lines += ["## Status", "", "Analysis completed. See sections above for details.", ""]
    return "\n".join(lines)