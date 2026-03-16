"""
LangGraph Workflow Graph
────────────────────────
Defines the full agent orchestration graph:

    START
      │
      ▼
   Planner ──────────────────────────────────┐
      │                                       │
      ▼                                       │
   Researcher                                 │
      │                                       │
      ▼                                       │
    Coder                                     │
      │                                       │
      ▼                                       │
   Executor                                   │
      │                                       │
      ▼                                       │
    Critic ──► fail ──► Coder (retry loop)   │
      │                                       │
      ├──► human_review ──► [await]           │
      │                                       │
      ▼ pass                                  │
   Reporter                                   │
      │                                       │
      ▼                                       │
     END ◄──────────────────────────────────┘

The graph supports:
  - Cyclic retry loop (Critic → Coder → Executor → Critic)
  - Human-in-the-loop pause state
  - Conditional routing based on agent verdicts
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.coder import CoderAgent
from agents.executor import ExecutorAgent
from agents.critic import CriticAgent
from agents.reporter import ReporterAgent

logger = logging.getLogger(__name__)

# ── Node name constants ────────────────────────────────────────────────────────
NODE_PLANNER = "planner"
NODE_RESEARCHER = "researcher"
NODE_CODER = "coder"
NODE_EXECUTOR = "executor"
NODE_CRITIC = "critic"
NODE_REPORTER = "reporter"


# ── Routing functions ──────────────────────────────────────────────────────────

def route_after_critic(
    state: AgentState,
) -> Literal["coder", "reporter", "__end__"]:
    """
    Decides the next node after Critic evaluation.

    - "fail"         → back to Coder for a retry
    - "human_review" → END (workflow paused; API layer picks it up)
    - "pass"         → forward to Reporter
    """
    verdict = state.get("critic_verdict", "pass")
    workflow = state.get("workflow_status", "running")

    if workflow in ("failed", "awaiting_human"):
        logger.info("Routing: workflow=%s → END", workflow)
        return END  # type: ignore[return-value]

    if verdict == "fail":
        logger.info("Routing: critic=fail → coder (retry)")
        return NODE_CODER

    logger.info("Routing: critic=pass → reporter")
    return NODE_REPORTER


def route_after_planner(state: AgentState) -> Literal["researcher", "__end__"]:
    """Short-circuit on planning failure."""
    if state.get("workflow_status") == "failed":
        return END  # type: ignore[return-value]
    return NODE_RESEARCHER


# ── Graph construction ─────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Construct and compile the LangGraph StateGraph.

    Returns a compiled graph ready to be invoked with an initial AgentState.
    """
    # Instantiate agents (each is a callable node)
    planner = PlannerAgent()
    researcher = ResearchAgent()
    coder = CoderAgent()
    executor = ExecutorAgent()
    critic = CriticAgent()
    reporter = ReporterAgent()

    # Build graph
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node(NODE_PLANNER, planner)
    graph.add_node(NODE_RESEARCHER, researcher)
    graph.add_node(NODE_CODER, coder)
    graph.add_node(NODE_EXECUTOR, executor)
    graph.add_node(NODE_CRITIC, critic)
    graph.add_node(NODE_REPORTER, reporter)

    # Entry point
    graph.set_entry_point(NODE_PLANNER)

    # Linear edges
    graph.add_conditional_edges(
        NODE_PLANNER,
        route_after_planner,
        {NODE_RESEARCHER: NODE_RESEARCHER, END: END},
    )
    graph.add_edge(NODE_RESEARCHER, NODE_CODER)
    graph.add_edge(NODE_CODER, NODE_EXECUTOR)
    graph.add_edge(NODE_EXECUTOR, NODE_CRITIC)

    # Conditional branching from Critic
    graph.add_conditional_edges(
        NODE_CRITIC,
        route_after_critic,
        {
            NODE_CODER: NODE_CODER,      # retry loop
            NODE_REPORTER: NODE_REPORTER, # success path
            END: END,                     # failure / human review
        },
    )

    # Reporter always terminates
    graph.add_edge(NODE_REPORTER, END)

    return graph.compile()


# ── Module-level compiled graph (lazy) ────────────────────────────────────────
_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        logger.info("Compiling LangGraph workflow…")
        _workflow = build_workflow()
        logger.info("Workflow compiled ✔")
    return _workflow
