"""
FastAPI Application — Nexus Autonomous Agent System
────────────────────────────────────────────────────
Endpoints:

  POST   /task                        Submit a new analysis task
  GET    /status/{task_id}            Poll workflow status
  GET    /result/{task_id}            Get final report
  POST   /confirm/{task_id}           Human-in-the-loop confirmation

  POST   /session                     Create a new user session
  GET    /session/{session_id}/tasks  List tasks owned by session
  POST   /chat/{task_id}              Chat about a completed report

  GET    /metrics                     System-wide metrics
  GET    /artifacts/{task_id}/{file}  Download artifact
  GET    /health                      Health check
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from agents.state import AgentState
from evaluation.metrics import get_metrics
from orchestration.workflow_graph import get_workflow
from dashboard.routes import router as dashboard_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Stores ─────────────────────────────────────────────────────────────────────
# task_id → AgentState
_task_store: dict[str, AgentState] = {}
_task_lock = asyncio.Lock()

# session_id → set of task_ids owned by that session
_session_store: dict[str, set[str]] = {}

# task_id → list of chat messages [{role, content}]
_chat_store: dict[str, list[dict]] = {}


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Nexus starting up")
    get_workflow()
    get_metrics()
    yield
    logger.info("Nexus shutting down")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Nexus — Autonomous Agent System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,      # disable public swagger
    redoc_url=None,     # disable public redoc
    openapi_url=None,   # disable openapi schema endpoint
)

app.include_router(dashboard_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────────
class TaskRequest(BaseModel):
    task: str = Field(..., min_length=10)
    session_id: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    session_id: str
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
    docx_path: str | None
    pdf_path: str | None
    artifacts: list[str]
    token_usage: dict[str, int]
    step_timings: dict[str, float]
    sources: list[str]

class ConfirmRequest(BaseModel):
    action: str = Field("proceed")
    feedback: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    intent: str          # "chat" | "replot" | "new_task"
    task_id: str
    new_artifacts: list[str]


# ── Session helpers ────────────────────────────────────────────────────────────
def _create_session() -> str:
    sid = str(uuid.uuid4())
    _session_store[sid] = set()
    return sid

def _register_task(session_id: str, task_id: str) -> None:
    if session_id not in _session_store:
        _session_store[session_id] = set()
    _session_store[session_id].add(task_id)

def _session_owns_task(session_id: str, task_id: str) -> bool:
    return task_id in _session_store.get(session_id, set())


# ── Workflow runner ────────────────────────────────────────────────────────────
async def _run_workflow(task_id: str, task_text: str, session_id: str) -> None:
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
    _register_task(session_id, task_id)

    try:
        workflow = get_workflow()
        loop = asyncio.get_event_loop()
        final_state: AgentState = await loop.run_in_executor(
            None, workflow.invoke, initial_state
        )
        async with _task_lock:
            _task_store[task_id] = final_state
        metrics.finish_task(task_id, final_state)
        logger.info("Workflow complete %s status=%s", task_id, final_state.get("workflow_status"))

    except Exception as exc:
        logger.exception("Workflow error %s: %s", task_id, exc)
        existing = _task_store.get(task_id, {})
        if existing.get("final_report"):
            recovery: AgentState = {**existing, "workflow_status": "complete"}
        else:
            recovery: AgentState = {
                **initial_state,
                "workflow_status": "failed",
                "error_message": "The workflow encountered an unexpected error. Please try again.",
            }
        async with _task_lock:
            _task_store[task_id] = recovery
        metrics.finish_task(task_id, recovery)


# ── Chat intent classifier + responder ────────────────────────────────────────
_CHAT_SYSTEM = """\
You are a helpful data analyst assistant. A user has just read an analysis report
and wants to discuss it or ask follow-up questions.

You have access to:
- The original report
- The research findings
- The generated code
- The list of artifacts (charts) produced

Your job:
1. Answer the user's question conversationally based on the report and data.
2. If the user asks to create a NEW chart, visualisation, or plot → set intent to "replot"
   and include a complete standalone Python script in your reply inside ```python ``` fences.
   The script must use _ARTIFACTS as the output path (it will be injected).
3. If the user asks a completely new analysis question unrelated to this report → set intent to "new_task"
4. Otherwise → set intent to "chat"

Return ONLY valid JSON:
{
  "intent": "chat" | "replot" | "new_task",
  "reply": "your conversational response",
  "code": "python code string if intent is replot, else empty string"
}

Rules:
- Never make up data not in the report
- Be concise but thorough
- For replot, always generate self-contained matplotlib code
- Never expose internal system details, errors, or stack traces
"""

async def _handle_chat(task_id: str, message: str) -> dict:
    """Classify intent and respond. Returns {intent, reply, new_artifacts}."""
    import json as _json
    from config.llm import build_llm

    state = _task_store.get(task_id, {})
    report    = state.get("final_report", "") or ""
    research  = state.get("research_summary", "") or ""
    code      = state.get("generated_code", "") or ""
    artifacts = state.get("execution_artifacts", []) or []

    # Build conversation history
    history = _chat_store.get(task_id, [])
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history[-6:]
    ) if history else ""

    prompt = f"""Report (excerpt):
{report[:2000]}

Research context:
{research[:800]}

Previous conversation:
{history_text}

User message: {message}

Respond with the JSON object.
"""

    llm = build_llm("primary")
    try:
        resp = llm.complete_json(prompt, system_prompt=_CHAT_SYSTEM)
        data = _json.loads(resp["content"])
    except Exception as exc:
        logger.warning("Chat LLM error: %s", exc)
        data = {"intent": "chat", "reply": "I couldn't process that. Could you rephrase?", "code": ""}

    intent      = data.get("intent", "chat")
    reply       = data.get("reply", "")
    gen_code    = data.get("code", "")
    new_artifacts: list[str] = []

    # If replot — execute the code
    if intent == "replot" and gen_code.strip():
        try:
            from tools.python_executor import PythonExecutorTool
            replot_id = f"{task_id}_chat_{len(history)}"
            result = PythonExecutorTool().execute(gen_code, task_id=replot_id)
            new_artifacts = result.get("artifacts", [])
            # Merge new artifacts into state
            async with _task_lock:
                existing_arts = _task_store[task_id].get("execution_artifacts", []) or []
                _task_store[task_id] = {
                    **_task_store[task_id],
                    "execution_artifacts": existing_arts + new_artifacts,
                }
            if not reply:
                reply = "I've created the visualisation for you."
        except Exception as exc:
            logger.warning("Replot execution failed: %s", exc)
            reply = "I tried to create the chart but ran into an issue. " + reply

    # Store message in history
    if task_id not in _chat_store:
        _chat_store[task_id] = []
    _chat_store[task_id].append({"role": "user", "content": message})
    _chat_store[task_id].append({"role": "assistant", "content": reply})

    return {"intent": intent, "reply": reply, "new_artifacts": new_artifacts}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/session")
async def create_session() -> JSONResponse:
    """Create a new user session. Returns a session_id the client must keep."""
    sid = _create_session()
    return JSONResponse({"session_id": sid})


@app.get("/session/{session_id}/tasks")
async def session_tasks(session_id: str) -> JSONResponse:
    """List tasks owned by this session only."""
    owned_ids = _session_store.get(session_id, set())
    tasks = []
    for tid in owned_ids:
        s = _task_store.get(tid)
        if s:
            task_text = s.get("original_task", "")
            tasks.append({
                "task_id": tid,
                "status": s.get("workflow_status", "unknown"),
                "task": task_text[:80] + ("…" if len(task_text) > 80 else ""),
                "subtasks": len(s.get("subtasks", [])),
                "retries": s.get("retry_count", 0),
            })
    return JSONResponse({"tasks": tasks, "total": len(tasks)})


@app.post("/task", response_model=TaskResponse, status_code=202)
async def submit_task(request: TaskRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    """Submit a new task. Requires a session_id."""
    session_id = request.session_id or _create_session()
    task_id    = str(uuid.uuid4())
    now        = datetime.utcnow().isoformat()

    background_tasks.add_task(
        _run_workflow,
        task_id=task_id,
        task_text=request.task,
        session_id=session_id,
    )

    logger.info("Task submitted: %s session: %s", task_id, session_id)
    return TaskResponse(
        task_id=task_id,
        session_id=session_id,
        status="accepted",
        message="Task accepted and workflow started",
        submitted_at=now,
    )


@app.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str, session_id: Optional[str] = None) -> StatusResponse:
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Session check — if session_id provided, must own the task
    if session_id and not _session_owns_task(session_id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")

    messages     = state.get("agent_messages", [])
    current_step = messages[-1]["agent"] if messages else "initialising"
    metrics      = get_metrics()
    m            = metrics.get_task(task_id)
    elapsed      = m["latency_s"] if m else None

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
async def get_result(task_id: str, session_id: Optional[str] = None) -> ResultResponse:
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if session_id and not _session_owns_task(session_id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")

    status = state.get("workflow_status", "running")
    if status == "running":
        raise HTTPException(status_code=202, detail="Task is still running")

    return ResultResponse(
        task_id=task_id,
        status=status,
        report=state.get("final_report", ""),
        report_path=state.get("report_path") or None,
        docx_path=state.get("docx_path") or None,
        pdf_path=state.get("pdf_path") or None,
        artifacts=state.get("execution_artifacts", []),
        token_usage=state.get("token_usage", {}),
        step_timings=state.get("step_timings", {}),
        sources=state.get("research_sources", []),
    )


@app.post("/chat/{task_id}", response_model=ChatResponse)
async def chat_about_report(task_id: str, request: ChatRequest) -> ChatResponse:
    """
    Conversational follow-up on a completed report.
    Smart routing: chat / replot / new_task.
    No research or full pipeline re-run unless explicitly needed.
    """
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    session_id = request.session_id
    if session_id and not _session_owns_task(session_id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if state.get("workflow_status") not in ("complete", "failed"):
        raise HTTPException(status_code=400, detail="Task must be complete before chatting")

    result = await _handle_chat(task_id, request.message)

    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        task_id=task_id,
        new_artifacts=result["new_artifacts"],
    )


@app.get("/chat/{task_id}/history")
async def get_chat_history(task_id: str, session_id: Optional[str] = None) -> JSONResponse:
    """Return the conversation history for a task."""
    if session_id and not _session_owns_task(session_id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")
    history = _chat_store.get(task_id, [])
    return JSONResponse({"history": history, "count": len(history)})


@app.post("/confirm/{task_id}")
async def confirm_task(
    task_id: str, request: ConfirmRequest, background_tasks: BackgroundTasks
) -> JSONResponse:
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not state.get("human_confirmation_needed"):
        raise HTTPException(status_code=400, detail="Task does not require confirmation")

    if request.action == "abort":
        async with _task_lock:
            _task_store[task_id] = {
                **state,
                "workflow_status": "failed",
                "human_confirmation_needed": False,
                "error_message": "Stopped by reviewer",
            }
        return JSONResponse({"message": "Task stopped"})

    resumed: AgentState = {
        **state,
        "workflow_status": "running",
        "human_confirmation_needed": False,
        "critic_verdict": "fail",
        "critic_feedback": request.feedback or "Please address all outstanding issues.",
    }
    async with _task_lock:
        _task_store[task_id] = resumed
    background_tasks.add_task(_resume_workflow, task_id, resumed)
    return JSONResponse({"message": "Task resumed", "task_id": task_id})


async def _resume_workflow(task_id: str, state: AgentState) -> None:
    metrics = get_metrics()
    try:
        workflow = get_workflow()
        loop = asyncio.get_event_loop()
        final_state: AgentState = await loop.run_in_executor(None, workflow.invoke, state)
        async with _task_lock:
            _task_store[task_id] = final_state
        metrics.finish_task(task_id, final_state)
    except Exception as exc:
        logger.exception("Resume error %s: %s", task_id, exc)


@app.get("/metrics")
async def system_metrics() -> JSONResponse:
    return JSONResponse(get_metrics().get_aggregates())


@app.get("/tasks")
async def list_tasks() -> JSONResponse:
    """Internal listing — returns minimal info, no task content."""
    summary = [
        {
            "task_id": tid,
            "status": s.get("workflow_status", "unknown"),
            "task": s.get("original_task", "")[:80],
            "subtasks": len(s.get("subtasks", [])),
            "retries": s.get("retry_count", 0),
        }
        for tid, s in _task_store.items()
    ]
    return JSONResponse({"tasks": summary, "total": len(summary)})


@app.get("/artifacts/{task_id}/{filename}")
async def get_artifact(task_id: str, filename: str) -> FileResponse:
    from config.settings import settings
    # Try configured dir first, then tmp
    for base in [settings.ARTIFACTS_DIR / task_id, Path(f"/tmp/artifacts/{task_id}"),
                 Path(f"/tmp/amas_{task_id}")]:
        p = base / filename
        if p.exists():
            return FileResponse(p)
    # Also check chat replot dirs
    import glob, os
    pattern = f"/tmp/amas_{task_id}_chat_*/{filename}"
    matches = glob.glob(pattern)
    if matches:
        return FileResponse(matches[0])
    raise HTTPException(status_code=404, detail="Artifact not found")


@app.get("/report/{task_id}/pdf")
async def download_pdf(task_id: str, session_id: Optional[str] = None) -> FileResponse:
    """Download the PDF report."""
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if session_id and not _session_owns_task(session_id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")

    pdf_path = state.get("pdf_path", "")
    if pdf_path and Path(pdf_path).exists():
        return FileResponse(pdf_path, media_type="application/pdf",
                            filename=f"report_{task_id[:8]}.pdf")

    from config.settings import settings
    candidates = [
        settings.ARTIFACTS_DIR / task_id / f"{task_id}_report.pdf",
        Path(f"/tmp/amas_{task_id}/{task_id}_report.pdf"),
        Path(f"/tmp/{task_id}_report.pdf"),
    ]
    for p in candidates:
        if p.exists():
            return FileResponse(str(p), media_type="application/pdf",
                                filename=f"report_{task_id[:8]}.pdf")
    raise HTTPException(status_code=404, detail="PDF not yet generated")


@app.get("/report/{task_id}/docx")
async def download_docx(task_id: str, session_id: Optional[str] = None) -> FileResponse:
    """Download the .docx report for a completed task."""
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if session_id and not _session_owns_task(session_id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")

    docx_path = state.get("docx_path", "")
    if docx_path and Path(docx_path).exists():
        return FileResponse(
            docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"report_{task_id[:8]}.docx",
        )

    # Try to find it
    from config.settings import settings
    import glob
    candidates = [
        settings.ARTIFACTS_DIR / task_id / f"{task_id}_report.docx",
        Path(f"/tmp/amas_{task_id}/{task_id}_report.docx"),
        Path(f"/tmp/{task_id}_report.docx"),
    ]
    for p in candidates:
        if p.exists():
            return FileResponse(
                str(p),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=f"report_{task_id[:8]}.docx",
            )
    raise HTTPException(status_code=404, detail="Report not yet generated or unavailable")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({
        "status": "healthy",
        "service": "nexus",
        "version": "1.0.0",
        "active_tasks": sum(1 for s in _task_store.values() if s.get("workflow_status") == "running"),
        "sessions": len(_session_store),
    })


@app.delete("/task/{task_id}")
async def delete_task(task_id: str, session_id: Optional[str] = None) -> JSONResponse:
    state = _task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if session_id and not _session_owns_task(session_id, task_id):
        raise HTTPException(status_code=403, detail="Access denied")
    if state.get("workflow_status") == "running":
        raise HTTPException(status_code=400, detail="Cannot delete a running task")
    del _task_store[task_id]
    _chat_store.pop(task_id, None)
    return JSONResponse({"message": "Task deleted"})