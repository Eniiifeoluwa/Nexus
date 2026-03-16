"""
Coder Agent
───────────
Generates executable Python code to complete the current subtask.
Takes into account:
  - The original task
  - The current subtask
  - The research summary
  - Critic feedback (on retries)

Code is written to produce artefacts (CSVs, PNGs, text files) that the
Executor and Report agents can pick up.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior Python data scientist and engineer.
Generate clean, complete, executable Python code to accomplish the given task.

CRITICAL RULES:
1. Output ONLY the raw Python code — no prose, no markdown fences, no explanation.
2. The code must be self-contained and runnable with no user input.
3. Save all output files to /tmp/artifacts/ — create this directory at the start.
4. For any dataset not provided, generate realistic synthetic data with numpy/pandas.
5. All plots must be saved as PNG files (use matplotlib/seaborn, never plt.show()).
6. Include try/except for I/O and numeric operations.
7. Print a JSON summary at the end: {"status": "success", "files": [...], "insights": [...]}
8. Use only these libraries: pandas, numpy, matplotlib, seaborn, scikit-learn, json, os, pathlib.
"""

_RETRY_ADDENDUM = """\
IMPORTANT — FIX THE FOLLOWING ISSUES from the previous attempt:
{feedback}

Do NOT repeat the previous errors. Produce corrected code only.
"""


class CoderAgent(BaseAgent):
    """Generates Python code for a subtask, incorporating critic feedback on retries."""

    LLM_ROLE = "code"

    def __init__(self) -> None:
        super().__init__("CoderAgent")

    def run(self, state: AgentState) -> dict[str, Any]:
        task = state.get("original_task", "")
        subtasks = state.get("subtasks", [])
        idx = state.get("current_subtask_index", 0)
        current_subtask = subtasks[idx] if subtasks else task
        research = state.get("research_summary", "")
        feedback = state.get("critic_feedback", "")
        retry_count = state.get("retry_count", 0)

        self.logger.info(
            "Generating code for subtask %d/%d (retry=%d): %s",
            idx + 1,
            len(subtasks),
            retry_count,
            current_subtask,
        )

        # Build prompt
        retry_section = ""
        if retry_count > 0 and feedback:
            retry_section = _RETRY_ADDENDUM.format(feedback=feedback)

        prompt = f"""
Task: {task}

Current subtask to implement: {current_subtask}

Research context:
{research or '(No research context available)'}

{retry_section}

Generate complete, executable Python code. Remember: output ONLY code, no fences.
"""
        response = self.llm.complete(prompt, system_prompt=_SYSTEM_PROMPT)
        raw = response["content"]

        # Strip accidental markdown fences if model ignored instruction
        code = _strip_fences(raw)

        self.logger.debug("Generated %d lines of code", code.count("\n"))
        return {"generated_code": code, "code_language": "python"}


def _strip_fences(text: str) -> str:
    """Remove ```python / ``` fences if the model included them."""
    text = re.sub(r"^```(?:python)?\s*\n", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\n```\s*$", "", text, flags=re.IGNORECASE)
    return text.strip()
