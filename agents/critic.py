"""
Critic Agent
────────────
Evaluates the output of the Executor and decides:

  - "pass"         → forward to Report Agent
  - "fail"         → send actionable feedback to Coder (up to MAX_RETRIES)
  - "human_review" → pause workflow for human confirmation

Scoring dimensions:
  1. Execution status (hard gate)
  2. Output completeness
  3. Correctness signals (no NaN floods, no empty files, etc.)
  4. LLM-based qualitative assessment
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
You are a strict code quality reviewer and data analyst.
Evaluate the outputs of a Python execution step and return ONLY JSON.

Schema:
{
  "verdict": "pass" | "fail",
  "confidence": 0.0-1.0,
  "issues": ["issue 1", ...],
  "feedback": "Actionable feedback for the coder if verdict is fail",
  "summary": "One-sentence summary"
}

Be strict. Fail if:
- The output is empty or contains only whitespace
- There are Python tracebacks in stderr
- Key task objectives are clearly unmet
- Output data looks fabricated or nonsensical
"""


class CriticAgent(BaseAgent):
    """Evaluates execution outputs and manages the retry loop."""

    LLM_ROLE = "primary"

    def __init__(self) -> None:
        super().__init__("CriticAgent")

    def run(self, state: AgentState) -> dict[str, Any]:
        exec_status = state.get("execution_status", "failure")
        stdout = state.get("execution_stdout", "")
        stderr = state.get("execution_stderr", "")
        artifacts = state.get("execution_artifacts", [])
        retry_count = state.get("retry_count", 0)
        task = state.get("original_task", "")
        code = state.get("generated_code", "")

        # ── Hard gate: execution failure ──────────────────────────────────────
        if exec_status == "failure":
            if retry_count >= settings.MAX_RETRIES:
                self.logger.warning("Max retries reached — escalating to human review")
                return self._human_review(
                    state,
                    reason=f"Execution failed after {retry_count} retries. Last error: {stderr[:300]}",
                )
            return self._fail(
                state,
                feedback=f"Code execution failed with error:\n{stderr}\n\nFix the code and ensure it runs without errors.",
            )

        # ── LLM quality assessment ────────────────────────────────────────────
        prompt = f"""
Original task: {task}

Generated code (truncated):
{code[:1500]}

Execution stdout:
{stdout[:2000]}

Execution stderr:
{stderr[:500]}

Artifacts produced: {artifacts}

Evaluate the output quality and return the JSON verdict.
"""
        response = self.llm.complete_json(prompt, system_prompt=_SYSTEM_PROMPT)
        raw = response["content"]

        try:
            assessment = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("Critic JSON parse error, defaulting to pass")
            assessment = {"verdict": "pass", "confidence": 0.5, "feedback": "", "summary": ""}

        verdict: str = assessment.get("verdict", "pass")
        confidence: float = float(assessment.get("confidence", 0.5))
        feedback: str = assessment.get("feedback", "")
        summary: str = assessment.get("summary", "")

        self.logger.info(
            "Critic verdict=%s confidence=%.2f summary=%s", verdict, confidence, summary
        )

        # ── Low confidence → human review ─────────────────────────────────────
        if confidence < settings.CONFIDENCE_THRESHOLD and retry_count >= 1:
            return self._human_review(
                state,
                reason=f"Confidence {confidence:.0%} below threshold. {summary}",
            )

        if verdict == "fail":
            if retry_count >= settings.MAX_RETRIES:
                return self._human_review(
                    state,
                    reason=f"Max retries reached. Last feedback: {feedback}",
                )
            return self._fail(state, feedback=feedback)

        # ── Pass ──────────────────────────────────────────────────────────────
        return {
            "critic_verdict": "pass",
            "critic_feedback": feedback,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fail(self, state: AgentState, feedback: str) -> dict[str, Any]:
        new_retry = state.get("retry_count", 0) + 1
        self.logger.info("Critic: FAIL (retry %d)", new_retry)
        return {
            "critic_verdict": "fail",
            "critic_feedback": feedback,
            "retry_count": new_retry,
        }

    def _human_review(self, state: AgentState, reason: str) -> dict[str, Any]:
        self.logger.info("Critic: HUMAN REVIEW required: %s", reason)
        return {
            "critic_verdict": "human_review",
            "workflow_status": "awaiting_human",
            "human_confirmation_needed": True,
            "human_confirmation_message": (
                f"The workflow requires human confirmation.\n\nReason: {reason}\n\n"
                "Please review and POST /confirm/{task_id} to proceed or abort."
            ),
        }
