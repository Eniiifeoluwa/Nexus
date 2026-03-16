"""
Planner Agent
─────────────
Accepts a free-form user task and decomposes it into an ordered list of
concrete, executable subtasks.  The output drives the entire downstream
workflow so the JSON schema is validated strictly.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert AI project planner. Your job is to decompose a complex user task
into a precise, ordered list of concrete subtasks that an AI agent system can execute.

Rules:
1. Each subtask must be actionable and self-contained.
2. Subtasks must be ordered logically (research before analysis, analysis before report).
3. Always include: research, data/code work, visualisation if applicable, and a final report.
4. Return ONLY valid JSON in this exact schema:
{
  "tasks": ["subtask 1", "subtask 2", ...]
}
No extra keys, no prose, no markdown fences.
"""


class PlannerAgent(BaseAgent):
    """Decomposes a user task into an ordered subtask list."""

    LLM_ROLE = "primary"

    def __init__(self) -> None:
        super().__init__("PlannerAgent")

    def run(self, state: AgentState) -> dict[str, Any]:
        task = state.get("original_task", "")
        if not task:
            return {"workflow_status": "failed", "error_message": "No task provided"}

        prompt = f"""
User Task: {task}

Decompose this into 5-8 ordered subtasks. Return the JSON object.
"""
        response = self.llm.complete_json(prompt, system_prompt=_SYSTEM_PROMPT)
        content = response["content"]

        try:
            parsed = json.loads(content)
            subtasks: list[str] = parsed.get("tasks", [])
            if not subtasks:
                raise ValueError("Empty task list returned")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Planner JSON parse error: %s  raw=%s", exc, content[:200])
            # Fallback: create generic subtasks
            subtasks = [
                f"Research: {task}",
                "Collect and load relevant datasets",
                "Perform exploratory data analysis",
                "Generate visualisations",
                "Write summary insights",
                "Produce final report",
            ]

        logger.info("Planner produced %d subtasks", len(subtasks))
        for i, t in enumerate(subtasks, 1):
            logger.debug("  %d. %s", i, t)

        return {
            "subtasks": subtasks,
            "current_subtask_index": 0,
            "retry_count": 0,
            "workflow_status": "running",
        }
