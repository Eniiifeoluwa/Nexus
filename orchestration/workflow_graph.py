"""
LangGraph Workflow Graph
────────────────────────
START → Planner → Researcher → Coder → Executor → Critic → Reporter → END

The Critic can send back to Coder once for a retry.
After that, everything goes to Reporter regardless — no dead ends.
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

NODE_PLANNER    = "planner"
NODE_RESEARCHER = "researcher"
NODE_CODER      = "coder"
NODE_EXECUTOR   = "executor"
NODE_CRITIC     = "critic"
NODE_REPORTER   = "reporter"


def route_after_planner(state: AgentState) -> str:
    if state.get("workflow_status") == "failed":
        # Even on planner failure, try to go to reporter with what we have
        return NODE_REPORTER
    return NODE_RESEARCHER


def route_after_critic(state: AgentState) -> str:
    verdict  = state.get("critic_verdict", "pass")
    workflow = state.get("workflow_status", "running")

    # Human review requested — pause here
    if workflow == "awaiting_human":
        logger.info("Routing: awaiting human review → END")
        return END  # type: ignore[return-value]

    # Hard failure with no recovery possible
    if workflow == "failed":
        logger.info("Routing: workflow failed → reporter anyway")
        return NODE_REPORTER

    # One retry allowed
    if verdict == "fail":
        retry = state.get("retry_count", 0)
        if retry <= 1:
            logger.info("Routing: critic=fail retry=%d → coder", retry)
            return NODE_CODER
        else:
            # Retries exhausted — go to reporter with what we have
            logger.info("Routing: retries exhausted → reporter")
            return NODE_REPORTER

    # Pass or anything else → reporter
    logger.info("Routing: critic=pass → reporter")
    return NODE_REPORTER


def build_workflow():
    planner    = PlannerAgent()
    researcher = ResearchAgent()
    coder      = CoderAgent()
    executor   = ExecutorAgent()
    critic     = CriticAgent()
    reporter   = ReporterAgent()

    graph = StateGraph(AgentState)

    graph.add_node(NODE_PLANNER,    planner)
    graph.add_node(NODE_RESEARCHER, researcher)
    graph.add_node(NODE_CODER,      coder)
    graph.add_node(NODE_EXECUTOR,   executor)
    graph.add_node(NODE_CRITIC,     critic)
    graph.add_node(NODE_REPORTER,   reporter)

    graph.set_entry_point(NODE_PLANNER)

    graph.add_conditional_edges(
        NODE_PLANNER,
        route_after_planner,
        {NODE_RESEARCHER: NODE_RESEARCHER, NODE_REPORTER: NODE_REPORTER},
    )
    graph.add_edge(NODE_RESEARCHER, NODE_CODER)
    graph.add_edge(NODE_CODER,      NODE_EXECUTOR)
    graph.add_edge(NODE_EXECUTOR,   NODE_CRITIC)

    graph.add_conditional_edges(
        NODE_CRITIC,
        route_after_critic,
        {
            NODE_CODER:     NODE_CODER,
            NODE_REPORTER:  NODE_REPORTER,
            END:            END,
        },
    )

    graph.add_edge(NODE_REPORTER, END)

    return graph.compile()


_workflow = None

def get_workflow():
    global _workflow
    if _workflow is None:
        logger.info("Compiling LangGraph workflow…")
        _workflow = build_workflow()
        logger.info("Workflow compiled")
    return _workflow