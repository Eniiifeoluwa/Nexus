"""
Shared state definitions for the LangGraph workflow.
Every agent reads from and writes to this TypedDict.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── Identity ───────────────────────────────────────────────────────────────
    task_id: str
    original_task: str

    # ── Planner outputs ────────────────────────────────────────────────────────
    subtasks: list[str]
    current_subtask_index: int

    # ── Research outputs ──────────────────────────────────────────────────────
    research_summary: str
    research_sources: list[str]

    # ── Coder outputs ─────────────────────────────────────────────────────────
    generated_code: str
    code_language: str

    # ── Executor outputs ──────────────────────────────────────────────────────
    execution_status: str          # "success" | "failure"
    execution_stdout: str
    execution_stderr: str
    execution_artifacts: list[str] # paths to generated files

    # ── Critic outputs ────────────────────────────────────────────────────────
    critic_verdict: str            # "pass" | "fail" | "human_review"
    critic_feedback: str
    retry_count: int

    # ── Report outputs ────────────────────────────────────────────────────────
    final_report: str
    report_path: str

    # ── Workflow control ──────────────────────────────────────────────────────
    workflow_status: str           # "running" | "complete" | "awaiting_human" | "failed"
    human_confirmation_needed: bool
    human_confirmation_message: str
    error_message: str

    # ── Metrics ───────────────────────────────────────────────────────────────
    token_usage: dict[str, int]
    step_timings: dict[str, float]
    agent_messages: list[dict[str, Any]]  # full audit trail
