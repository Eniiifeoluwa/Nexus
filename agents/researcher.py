"""
Research Agent
──────────────
Gathers information for the current subtask via:
  1. Web search (DuckDuckGo)
  2. Vector memory retrieval (ChromaDB)
  3. LLM-based summarisation of gathered context

Outputs a structured research summary stored in agent state.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base import BaseAgent
from agents.state import AgentState
from tools.web_search import WebSearchTool
from tools.vector_search import VectorSearchTool

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a research analyst. Given a task and raw source material,
produce a concise, factual research summary that will help a coder
write accurate Python code to complete the task.

Structure your output as:
## Summary
[2-4 paragraph summary]

## Key Facts
- [bullet list of important data points, numbers, or findings]

## Recommended Approach
[Brief technical recommendation for implementing the task in Python]
"""


class ResearchAgent(BaseAgent):
    """Performs web + vector search and summarises findings."""

    LLM_ROLE = "fast"

    def __init__(self) -> None:
        super().__init__("ResearchAgent")
        self.web_search = WebSearchTool()
        self.vector_search = VectorSearchTool()

    def run(self, state: AgentState) -> dict[str, Any]:
        task = state.get("original_task", "")
        subtasks = state.get("subtasks", [])
        idx = state.get("current_subtask_index", 0)
        current_subtask = subtasks[idx] if subtasks else task

        self.logger.info("Researching: %s", current_subtask)

        # ── 1. Web search ─────────────────────────────────────────────────────
        web_results = self.web_search.search(current_subtask, max_results=5)
        web_text = "\n\n".join(
            f"[{r['title']}]\n{r['snippet']}" for r in web_results
        )

        # ── 2. Vector memory search ───────────────────────────────────────────
        memory_results = self.vector_search.search(current_subtask, top_k=3)
        memory_text = "\n\n".join(
            f"[Memory {i+1}]\n{r}" for i, r in enumerate(memory_results)
        )

        sources = [r.get("url", "") for r in web_results if r.get("url")]

        # ── 3. LLM summarisation ──────────────────────────────────────────────
        context_block = ""
        if web_text.strip():
            context_block += f"\n\n=== WEB SEARCH RESULTS ===\n{web_text}"
        if memory_text.strip():
            context_block += f"\n\n=== MEMORY CONTEXT ===\n{memory_text}"

        if not context_block.strip():
            context_block = "(No external data retrieved; use general knowledge.)"

        prompt = f"""
Task: {task}
Current subtask: {current_subtask}

Available context:{context_block}

Produce a structured research summary to guide Python implementation.
"""
        response = self.llm.complete(prompt, system_prompt=_SYSTEM_PROMPT)
        summary = response["content"]

        # ── 4. Store summary in vector memory for future retrieval ────────────
        self.vector_search.store(
            text=summary,
            metadata={"task_id": state.get("task_id", ""), "subtask": current_subtask},
        )

        return {
            "research_summary": summary,
            "research_sources": sources,
        }
