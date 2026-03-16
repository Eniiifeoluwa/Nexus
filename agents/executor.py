"""
Executor Agent
──────────────
Safely runs generated Python code, capturing stdout/stderr and any
files written to /tmp/artifacts/.

Execution back-ends (in priority order):
  1. Docker sandbox  — full isolation (requires Docker daemon)
  2. subprocess      — in-process fallback with resource limits

Returns structured execution results into the agent state.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState
from tools.python_executor import PythonExecutorTool

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """Executes generated Python code in a sandboxed environment."""

    LLM_ROLE = "fast"  # Executor doesn't call the LLM; role doesn't matter here

    def __init__(self) -> None:
        super().__init__("ExecutorAgent")
        self.executor = PythonExecutorTool()

    def run(self, state: AgentState) -> dict[str, Any]:
        code = state.get("generated_code", "")
        task_id = state.get("task_id", "unknown")

        if not code:
            return {
                "execution_status": "failure",
                "execution_stdout": "",
                "execution_stderr": "No code to execute",
                "execution_artifacts": [],
            }

        self.logger.info("Executing code for task %s (%d chars)", task_id, len(code))

        result = self.executor.execute(code, task_id=task_id)

        status = "success" if result["exit_code"] == 0 else "failure"

        if status == "success":
            self.logger.info(
                "Execution succeeded. Artifacts: %s", result.get("artifacts", [])
            )
        else:
            self.logger.warning(
                "Execution failed. stderr: %s", result.get("stderr", "")[:300]
            )

        return {
            "execution_status": status,
            "execution_stdout": result.get("stdout", ""),
            "execution_stderr": result.get("stderr", ""),
            "execution_artifacts": result.get("artifacts", []),
        }
