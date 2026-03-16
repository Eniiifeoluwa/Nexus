"""
Base agent class providing logging, timing, token accumulation,
and a consistent call interface for all concrete agents.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from agents.state import AgentState
from config.llm import GroqLLMWrapper, build_llm

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base for every agent in the system.

    Subclasses must implement `run(state)` which receives the shared
    AgentState and returns a (partial) AgentState dict with only the
    keys the agent mutated.
    """

    #: Override in subclasses to choose the LLM role (primary/fast/code)
    LLM_ROLE: str = "primary"

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self.llm: GroqLLMWrapper = build_llm(self.LLM_ROLE)

    # ── Public interface ──────────────────────────────────────────────────────

    def __call__(self, state: AgentState) -> AgentState:
        """LangGraph node interface — wraps `run` with timing & audit trail."""
        start = time.perf_counter()
        self.logger.info("▶ %s starting", self.name)

        try:
            updates = self.run(state)
        except Exception as exc:
            self.logger.exception("✗ %s failed: %s", self.name, exc)
            updates = {
                "workflow_status": "failed",
                "error_message": f"{self.name} error: {exc}",
            }

        elapsed = round(time.perf_counter() - start, 3)
        self.logger.info("✔ %s finished in %.3fs", self.name, elapsed)

        # Accumulate step timings
        existing_timings: dict = state.get("step_timings", {})
        existing_timings[self.name] = elapsed

        # Accumulate token usage
        existing_tokens: dict = state.get("token_usage", {})
        used = self.llm.total_tokens_used
        existing_tokens[self.name] = used
        self.llm.reset_token_counter()

        # Append to audit trail
        messages: list = state.get("agent_messages", [])
        messages.append(
            {
                "agent": self.name,
                "elapsed_s": elapsed,
                "tokens": used,
                "summary": self._summarise(updates),
            }
        )

        merged: AgentState = {
            **state,
            **updates,
            "step_timings": existing_timings,
            "token_usage": existing_tokens,
            "agent_messages": messages,
        }
        return merged

    @abstractmethod
    def run(self, state: AgentState) -> dict[str, Any]:
        """Execute agent logic; return partial state updates."""
        ...

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _summarise(self, updates: dict) -> str:
        keys = ", ".join(updates.keys()) if updates else "—"
        return f"updated: {keys}"
