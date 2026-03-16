"""
Research Agent
──────────────
Gathers information and produces a research summary.
Robust — works even when web search and vector memory are both unavailable.
Falls back to LLM general knowledge so the pipeline always continues.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a research analyst and data science expert.
Produce a detailed, factual research summary that will guide a Python coder
to implement a complete data analysis.

Your summary MUST include:

## Summary
A 3-4 paragraph overview of the topic with real-world context and numbers.

## Key Facts & Data Points
- Specific numbers, percentages, and statistics relevant to the task
- Known datasets or data sources that would be relevant
- Key trends and patterns

## Recommended Python Implementation
A concrete technical plan covering:
- What synthetic data to generate (columns, ranges, realistic values)
- What statistical methods to apply
- What chart types to create (with specific variable names)
- What insights to look for

Be specific with numbers. For example: "EV sales grew from 1M units in 2018 to 14M in 2023".
"""


class ResearchAgent(BaseAgent):
    """Produces a research summary, with web search as optional enhancement."""

    LLM_ROLE = "primary"

    def __init__(self) -> None:
        super().__init__("ResearchAgent")

    def run(self, state: AgentState) -> dict[str, Any]:
        task     = state.get("original_task", "")
        subtasks = state.get("subtasks", [])
        idx      = state.get("current_subtask_index", 0)
        focus    = subtasks[idx] if subtasks else task

        self.logger.info("Researching: %s", focus[:80])

        # ── 1. Try web search (non-fatal if it fails) ─────────────────────────
        web_context = ""
        sources: list[str] = []
        try:
            from tools.web_search import WebSearchTool
            results = WebSearchTool().search(task, max_results=4)
            if results:
                web_context = "\n\n".join(
                    f"[{r['title']}]\n{r['snippet']}" for r in results
                )
                sources = [r["url"] for r in results if r.get("url")]
                self.logger.info("Web search returned %d results", len(results))
        except Exception as exc:
            self.logger.warning("Web search unavailable: %s — using LLM knowledge", exc)

        # ── 2. Try vector memory (non-fatal if it fails) ──────────────────────
        memory_context = ""
        try:
            from tools.vector_search import VectorSearchTool
            hits = VectorSearchTool().search(task, top_k=2)
            if hits:
                memory_context = "\n\n".join(hits)
        except Exception as exc:
            self.logger.debug("Vector memory unavailable: %s", exc)

        # ── 3. Build context block ────────────────────────────────────────────
        context = ""
        if web_context:
            context += f"\n\n### Web Search Results\n{web_context}"
        if memory_context:
            context += f"\n\n### Relevant Memory\n{memory_context}"
        if not context:
            context = "\n\n(Use your training knowledge — be specific with numbers and data.)"

        # ── 4. LLM summarisation — always runs ───────────────────────────────
        prompt = f"""Task: {task}

Current focus: {focus}

Available context:{context}

Produce a detailed research summary and Python implementation plan.
Be very specific with data ranges and numbers so the coder can generate realistic synthetic data.
"""
        response = self.llm.complete(prompt, system_prompt=_SYSTEM_PROMPT)
        summary = response["content"]

        # ── 5. Store in memory (non-fatal) ────────────────────────────────────
        try:
            from tools.vector_search import VectorSearchTool
            VectorSearchTool().store(
                text=summary,
                metadata={"task_id": state.get("task_id", ""), "subtask": focus},
            )
        except Exception:
            pass

        return {
            "research_summary": summary,
            "research_sources": sources,
        }