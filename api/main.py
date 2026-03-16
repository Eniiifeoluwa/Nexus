"""
FastAPI Application — Autonomous Multi-Agent System API
────────────────────────────────────────────────────────
Endpoints:

  POST   /task                  Submit a new task (async)
  GET    /status/{task_id}      Poll workflow status
  GET    /result/{task_id}      Retrieve final report
  POST   /confirm/{task_id}     Human-in-the-loop confirmation
  GET    /metrics               Aggregated system metrics
  GET    /metrics/{task_id}     Per-task metrics
  GET    /tasks                 List all submitted tasks
  GET    /health                Health check
  DELETE /task/{task_id}        Cancel / remove a task
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# ── App-internal imports ───────────────────────────────────────────────────────
from agents.state import AgentState
from evaluation.metrics import get_metrics
from orchestration.workflow_graph import get_workflow

from dashboard.routes import router as dashboard_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── In-memory task registry ────────────────────────────────────────────────────
# Maps task_id → AgentState (terminal or live)
_task_store: dict[str, AgentState] = {}
_task_lock = asyncio.Lock()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Autonomous Agent System starting up…")
    # Warm up workflow graph and metrics
    get_workflow()
    get_metrics()
    yield
    logger.info("🛑 Autonomous Agent System shutting down.")


# ── App creation ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Autonomous Multi-Agent AI System",
    description=(
        "Production-grade agentic AI pipeline powered by Groq LLMs and LangGraph. "
        "Supports Planner → Researcher → Coder → Executor → Critic → Reporter workflows."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(dashboard_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str = Field(..., min_length=10, description="The task for the agent system to complete")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Optional metadata")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    submitted_at: str


class StatusResponse(BaseModel):
    task_id: str
    status: str
    workflow_status: str
    current_step: str
    retry_count: int
    subtasks: list[str]
    human_confirmation_needed: bool
    human_confirmation_message: str
    elapsed_s: float | None
    error: str | None


class ResultResponse(BaseModel):
    task_id: str
    status: str
    report: str
    report_path: str | None
    artifacts: list[str]
    token_usage: dict[str, int]
    step_timings: dict[str, float]
    sources: list[str]


class ConfirmRequest(BaseModel):
    action: str = Field("proceed", description="'proceed' or 'abort'")
    feedback: Optional[str] = Field(None, description="Optional human feedback")


# ── Background task runner ─────────────────────────────────────────────────────

async def _run_workflow(task_id: str, task_text: str, metadata: dict) -> None:
    """Execute the full agent workflow in the background."""
    metrics = get_metrics()
    metrics.start_task(task_id, task_text)

    initial_state: AgentState = {
        "task_id": task_id,
        "original_task": task_text,
        "subtasks": [],
        "current_subtask_index": 0,
        "research_summary": "",
        "research_sources": [],
        "generated_code": "",
        "code_language": "python",
        "execution_status": "",
        "execution_stdout": "",
        "execution_stderr": "",
        "execution_artifacts": [],
        "critic_verdict": "",
        "critic_feedback": "",
        "retry_count": 0,
        "final_report": "",
        "report_path": "",
        "workflow_status": "running",
        "human_confirmation_needed": False,
        "human_confirmation_message": "",
        "error_message": "",
        "token_usage": {},
        "step_timings": {},
        "agent_messages": [],
    }

    async with _task_lock:
        _task_store[task_id] = initial_state

    try:
        workflow = get_workflow()
        logger.info("▶ Workflow started for task %s", task_id)

        # LangGraph invoke is synchronous; run in executor thread
        loop = asyncio.get_event_loop()
        final_state: AgentState = await loop.run_in_executor(
            None, workflow.invoke, initial_state
        )

        async with _task_lock:
            _task_store[task_id] = final_state

        metrics.finish_task(task_id, final_state)
        logger.info(
            "✔ Workflow complete for task %s — status=%s",
            task_id,
            final_state.get("workflow_status"),
        )

    except Exception as exc:
        logger.exception("Workflow error for task %s: %s", task_id, exc)
        error_state: AgentState = {
            **initial_state,
            "workflow_status": "failed",
            "error_message": str(exc),
        }
        async with _task_lock:
            _task_store[task_id] = error_state
        metrics.finish_task(task_id, error_state)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/task", response_model=TaskResponse, status_code=202)
async def submit_task(
    request: TaskRequest, background_tasks: BackgroundTasks
) -> TaskResponse:
    """Submit a new task to the agent system (non-blocking)."""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    background_tasks.add_task(
        _run_workflow,
        task_id=task_id,
        task_text=request.task,
        metadata=request.metadata or {},
    )

    logger.info("Task submitted: %s — %r", task_id, request.task[:80])
    return TaskResponse(
        task_id=task_id,
        status="accepted",
        message="Task accepted and workflow started",
        submitted_at=now,
    )


@app.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str) -> StatusResponse:
    """Poll the current status of a running or completed task."""
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")

    # Determine current step from last agent_message
    messages = state.get("agent_messages", [])
    current_step = messages[-1]["agent"] if messages else "initialising"

    # Compute elapsed time from metrics
    metrics = get_metrics()
    m = metrics.get_task(task_id)
    elapsed = m["latency_s"] if m else None

    return StatusResponse(
        task_id=task_id,
        status=state.get("workflow_status", "running"),
        workflow_status=state.get("workflow_status", "running"),
        current_step=current_step,
        retry_count=state.get("retry_count", 0),
        subtasks=state.get("subtasks", []),
        human_confirmation_needed=state.get("human_confirmation_needed", False),
        human_confirmation_message=state.get("human_confirmation_message", ""),
        elapsed_s=elapsed,
        error=state.get("error_message") or None,
    )


@app.get("/result/{task_id}", response_model=ResultResponse)
async def get_result(task_id: str) -> ResultResponse:
    """Retrieve the final structured report and artefacts for a completed task."""
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")

    status = state.get("workflow_status", "running")
    if status == "running":
        raise HTTPException(status_code=202, detail="Task is still running")

    return ResultResponse(
        task_id=task_id,
        status=status,
        report=state.get("final_report", ""),
        report_path=state.get("report_path") or None,
        artifacts=state.get("execution_artifacts", []),
        token_usage=state.get("token_usage", {}),
        step_timings=state.get("step_timings", {}),
        sources=state.get("research_sources", []),
    )


@app.post("/confirm/{task_id}")
async def confirm_task(
    task_id: str, request: ConfirmRequest, background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Human-in-the-loop confirmation endpoint.

    POST {"action": "proceed"} to resume the workflow.
    POST {"action": "abort"}   to terminate.
    """
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")

    if not state.get("human_confirmation_needed"):
        raise HTTPException(
            status_code=400, detail="Task does not require human confirmation"
        )

    if request.action == "abort":
        async with _task_lock:
            _task_store[task_id] = {
                **state,
                "workflow_status": "failed",
                "human_confirmation_needed": False,
                "error_message": "Aborted by human reviewer",
            }
        return JSONResponse({"message": "Task aborted"})

    # Proceed: inject human feedback and re-run from Coder
    resumed_state: AgentState = {
        **state,
        "workflow_status": "running",
        "human_confirmation_needed": False,
        "critic_verdict": "fail",  # force Coder retry
        "critic_feedback": (
            request.feedback
            or "Human reviewer requested a retry. Please address all outstanding issues."
        ),
    }

    async with _task_lock:
        _task_store[task_id] = resumed_state

    background_tasks.add_task(_resume_workflow, task_id, resumed_state)
    return JSONResponse({"message": "Task resumed", "task_id": task_id})


async def _resume_workflow(task_id: str, state: AgentState) -> None:
    """Resume a paused workflow from its current state."""
    metrics = get_metrics()
    try:
        workflow = get_workflow()
        loop = asyncio.get_event_loop()
        final_state: AgentState = await loop.run_in_executor(
            None, workflow.invoke, state
        )
        async with _task_lock:
            _task_store[task_id] = final_state
        metrics.finish_task(task_id, final_state)
    except Exception as exc:
        logger.exception("Resume workflow error for %s: %s", task_id, exc)


@app.get("/metrics")
async def system_metrics() -> JSONResponse:
    """Aggregated system-wide metrics."""
    return JSONResponse(get_metrics().get_aggregates())


@app.get("/metrics/{task_id}")
async def task_metrics(task_id: str) -> JSONResponse:
    """Per-task metrics including token usage and step timings."""
    m = get_metrics().get_task(task_id)
    if m is None:
        raise HTTPException(status_code=404, detail=f"No metrics for task {task_id!r}")
    return JSONResponse(m)


@app.get("/tasks")
async def list_tasks() -> JSONResponse:
    """List all submitted tasks with basic status."""
    summary = [
        {
            "task_id": tid,
            "status": s.get("workflow_status", "unknown"),
            "task": (s.get("original_task", "")[:80] + "…")
            if len(s.get("original_task", "")) > 80
            else s.get("original_task", ""),
            "subtasks": len(s.get("subtasks", [])),
            "retries": s.get("retry_count", 0),
        }
        for tid, s in _task_store.items()
    ]
    return JSONResponse({"tasks": summary, "total": len(summary)})


@app.get("/artifacts/{task_id}/{filename}")
async def get_artifact(task_id: str, filename: str) -> FileResponse:
    """Download a generated artefact file."""
    from config.settings import settings

    path = settings.ARTIFACTS_DIR / task_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path)


@app.get("/health")
async def health() -> JSONResponse:
    """Basic health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "autonomous-agent-system",
            "version": "1.0.0",
            "active_tasks": sum(
                1
                for s in _task_store.values()
                if s.get("workflow_status") == "running"
            ),
        }
    )


@app.delete("/task/{task_id}")
async def delete_task(task_id: str) -> JSONResponse:
    """Remove a task record (completed tasks only)."""
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")
    if state.get("workflow_status") == "running":
        raise HTTPException(status_code=400, detail="Cannot delete a running task")
    del _task_store[task_id]
    return JSONResponse({"message": f"Task {task_id} deleted"})
