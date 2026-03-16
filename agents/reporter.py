"""
Report Agent
────────────
Compiles all agent outputs into a structured Markdown report.
Robust — always produces a report even if execution partially failed.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState
from config.settings import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a professional technical report writer.
Given information about a completed AI analysis workflow, write a polished Markdown report.

Include these sections using ## headings:
1. Executive Summary
2. Methodology
3. Key Findings & Insights
4. Visualisations (list any image file paths)
5. Conclusions & Recommendations
6. Appendix — Generated Code (first 800 chars)

Write clearly and professionally. Only state what the data actually shows.
If some steps failed or produced limited output, write the best report possible
with what is available — do not mention pipeline failures in the report itself.
"""


class ReporterAgent(BaseAgent):
    LLM_ROLE = "primary"

    def __init__(self) -> None:
        super().__init__("ReporterAgent")

    def run(self, state: AgentState) -> dict[str, Any]:
        task       = state.get("original_task", "")
        subtasks   = state.get("subtasks", [])
        research   = state.get("research_summary", "") or ""
        stdout     = state.get("execution_stdout", "") or ""
        artifacts  = state.get("execution_artifacts", []) or []
        code       = state.get("generated_code", "") or ""
        token_usage = state.get("token_usage", {}) or {}
        timings    = state.get("step_timings", {}) or {}
        sources    = state.get("research_sources", []) or []
        task_id    = state.get("task_id", "unknown")

        # Extract JSON summary if code printed one
        insights_json = _extract_json_summary(stdout)
        insights_text = (
            json.dumps(insights_json, indent=2)
            if insights_json
            else (stdout[:2000] if stdout.strip() else "(No execution output available)")
        )

        viz_lines = "\n".join(f"- `{a}`" for a in artifacts if a.endswith(".png")) or "_None generated._"

        prompt = f"""
Task: {task}

Subtasks completed:
{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(subtasks))}

Research summary:
{research[:1200] or "(none)"}

Execution output / insights:
{insights_text}

Artifacts produced:
{chr(10).join(f"- {a}" for a in artifacts) or "(none)"}

Visualisations:
{viz_lines}

Sources:
{chr(10).join(f"- {s}" for s in sources[:5]) or "(none)"}

Code excerpt:
```python
{code[:800]}
```

Write a professional Markdown report now.
"""
        response = self.llm.complete(prompt, system_prompt=_SYSTEM_PROMPT)
        report_md = response["content"]

        # Metadata footer
        total_tokens = sum(token_usage.values())
        total_time   = sum(timings.values())
        report_md += f"""

---
## Workflow Summary

| | |
|---|---|
| Tokens used | {total_tokens:,} |
| Wall time | {total_time:.1f}s |
| Artifacts | {len(artifacts)} |
| Subtasks | {len(subtasks)} |
"""

        # Save to disk
        report_path = settings.ARTIFACTS_DIR / f"{task_id}_report.md"
        try:
            report_path.write_text(report_md, encoding="utf-8")
            logger.info("Report saved to %s", report_path)
        except Exception as exc:
            logger.warning("Could not save report: %s", exc)

        return {
            "final_report": report_md,
            "report_path": str(report_path),
            "workflow_status": "complete",
            "error_message": "",
        }


def _extract_json_summary(stdout: str) -> dict | None:
    import re
    if not stdout:
        return None
    matches = re.findall(r"\{[^{}]*\}", stdout, re.DOTALL)
    for m in reversed(matches):
        try:
            return json.loads(m)
        except json.JSONDecodeError:
            continue
    return None