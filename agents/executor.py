"""
Executor Agent
──────────────
Runs generated Python code and captures all output.
Always returns a result — never crashes the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState
from tools.python_executor import PythonExecutorTool

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    LLM_ROLE = "fast"

    def __init__(self) -> None:
        super().__init__("ExecutorAgent")
        self.executor = PythonExecutorTool()

    def run(self, state: AgentState) -> dict[str, Any]:
        code    = state.get("generated_code", "") or ""
        task_id = state.get("task_id", "unknown")

        if not code.strip():
            logger.warning("Executor: no code to run")
            return {
                "execution_status": "failure",
                "execution_stdout": "",
                "execution_stderr": "No code was generated.",
                "execution_artifacts": [],
            }

        logger.info("Executor: running %d chars of code", len(code))

        try:
            result = self.executor.execute(code, task_id=task_id)
        except Exception as exc:
            logger.exception("Executor tool crashed: %s", exc)
            return {
                "execution_status": "failure",
                "execution_stdout": "",
                "execution_stderr": f"Execution environment error: {exc}",
                "execution_artifacts": [],
            }

        exit_code = result.get("exit_code", 1)
        stdout    = result.get("stdout", "") or ""
        stderr    = result.get("stderr", "") or ""
        artifacts = result.get("artifacts", []) or []
        status    = "success" if exit_code == 0 else "failure"

        if status == "success":
            logger.info("Execution succeeded. Artifacts: %s", artifacts)
        else:
            logger.warning("Execution failed (exit=%d). stderr: %s", exit_code, stderr[:400])

        # If execution failed but produced some stdout, treat as partial success
        # so the Reporter can still use whatever output was generated
        if status == "failure" and stdout.strip():
            logger.info("Partial output detected — treating as partial success")
            status = "success"

        return {
            "execution_status": status,
            "execution_stdout": stdout,
            "execution_stderr": stderr,
            "execution_artifacts": artifacts,
        }