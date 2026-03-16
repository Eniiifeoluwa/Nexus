"""
Critic Agent
────────────
Evaluates executor output. Single-pass only — reviews once and either
passes or escalates. Never loops back more than once to the Coder.

Security: user-facing messages never expose internal errors or stack traces.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState
from config.settings import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a strict but fair code output reviewer.
Evaluate the result of a Python execution and return ONLY valid JSON.

Schema:
{
  "verdict": "pass" | "fail",
  "confidence": 0.0-1.0,
  "issues": ["issue 1", ...],
  "feedback": "Specific, actionable fix instructions for the coder if verdict is fail",
  "summary": "One sentence summary"
}

Pass if:
- Code ran without fatal errors
- Output contains meaningful data or analysis
- At least one insight or result was produced

Fail ONLY if:
- There is a clear Python traceback with no output at all
- The task objective was completely missed

Be lenient on minor issues. Partial success = pass.
Do not fail just because data is synthetic or charts are simple.
"""

# What users see — never the raw internal reason
_HUMAN_REVIEW_MESSAGE = (
    "The pipeline paused before producing the final report. "
    "You can provide additional guidance below, or continue to generate "
    "the report with the current results."
)


class CriticAgent(BaseAgent):
    """Single-pass output evaluator. Reviews once, never retries more than once."""

    LLM_ROLE = "primary"

    def __init__(self) -> None:
        super().__init__("CriticAgent")

    def run(self, state: AgentState) -> dict[str, Any]:
        exec_status = state.get("execution_status", "failure")
        stdout      = state.get("execution_stdout", "")
        stderr      = state.get("execution_stderr", "")
        artifacts   = state.get("execution_artifacts", [])
        retry_count = state.get("retry_count", 0)
        task        = state.get("original_task", "")
        code        = state.get("generated_code", "")

        # ── Hard limit: only one retry ever ───────────────────────────────────
        # If we've already retried once, pass through regardless and let
        # the Reporter work with whatever was produced.
        if retry_count >= 1:
            self.logger.info("Critic: retry limit reached — passing through to reporter")
            return {
                "critic_verdict": "pass",
                "critic_feedback": "",
            }

        # ── Execution failed with no output at all ────────────────────────────
        if exec_status == "failure" and not stdout.strip():
            if retry_count == 0:
                # Allow exactly one retry with a concrete fix instruction
                fix = _extract_fix_hint(stderr)
                self.logger.info("Critic: execution failed, allowing one retry")
                return self._retry(state, feedback=fix)
            else:
                # Already retried — move on
                return {"critic_verdict": "pass", "critic_feedback": ""}

        # ── LLM quality assessment ────────────────────────────────────────────
        prompt = f"""
Task: {task}

Code (first 1000 chars):
{code[:1000]}

Stdout:
{stdout[:1500]}

Stderr (last 300 chars):
{stderr[-300:] if stderr else "(none)"}

Artifacts produced: {artifacts}

Evaluate and return the JSON verdict.
"""
        response = self.llm.complete_json(prompt, system_prompt=_SYSTEM_PROMPT)
        try:
            assessment = json.loads(response["content"])
        except json.JSONDecodeError:
            # If we can't parse the assessment, pass through
            assessment = {"verdict": "pass", "confidence": 0.7, "feedback": "", "summary": ""}

        verdict    = assessment.get("verdict", "pass")
        confidence = float(assessment.get("confidence", 0.7))
        feedback   = assessment.get("feedback", "")
        summary    = assessment.get("summary", "")

        self.logger.info("Critic verdict=%s confidence=%.2f", verdict, confidence)

        # ── Low confidence on first attempt → one retry ───────────────────────
        if verdict == "fail" and retry_count == 0:
            return self._retry(state, feedback=feedback)

        # ── Very low confidence → human review (once only) ────────────────────
        if confidence < settings.CONFIDENCE_THRESHOLD and retry_count >= 1:
            return self._human_review(state)

        # ── Pass ──────────────────────────────────────────────────────────────
        return {
            "critic_verdict": "pass",
            "critic_feedback": "",
        }

    def _retry(self, state: AgentState, feedback: str) -> dict[str, Any]:
        self.logger.info("Critic: requesting one code retry")
        return {
            "critic_verdict": "fail",
            "critic_feedback": feedback or "Please fix any errors and ensure the code runs completely.",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    def _human_review(self, state: AgentState) -> dict[str, Any]:
        self.logger.info("Critic: escalating to human review")
        return {
            "critic_verdict": "human_review",
            "workflow_status": "awaiting_human",
            "human_confirmation_needed": True,
            "human_confirmation_message": _HUMAN_REVIEW_MESSAGE,
        }


def _extract_fix_hint(stderr: str) -> str:
    """Extract a clean, actionable fix from stderr without exposing internals."""
    if not stderr:
        return "Ensure the code runs completely and saves all output files."

    lines = [l.strip() for l in stderr.strip().splitlines() if l.strip()]

    # Find the actual error line (last non-empty line is usually the error type)
    for line in reversed(lines):
        if any(err in line for err in ("Error:", "Exception:", "error:")):
            # Return a sanitised hint, not the raw traceback
            if "ModuleNotFoundError" in line or "ImportError" in line:
                return "A required library is missing. Use only: pandas, numpy, matplotlib, seaborn, scikit-learn, json, os, pathlib."
            if "FileNotFoundError" in line or "PermissionError" in line:
                return "Use _ARTIFACTS as the output directory. Do not write to any other path."
            if "NameError" in line:
                return "A variable was used before it was defined. Check all variable names."
            if "ValueError" in line or "TypeError" in line:
                return "A data type or value error occurred. Add input validation and type checks."
            if "SyntaxError" in line:
                return "The code contains a syntax error. Review the code structure carefully."
            break

    return "Fix any runtime errors and ensure the code completes without exceptions."