# Autonomous Multi-Agent AI Workflow System

A production-grade autonomous AI pipeline powered by **Groq LLMs**, **LangGraph**, **FastAPI**, **ChromaDB**, and a Docker code sandbox. The system accepts complex tasks, decomposes them, researches them, writes and executes Python code, self-evaluates, and produces structured Markdown reports — all autonomously.

```
User Task → Planner → Researcher → Coder → Executor → Critic → Reporter → Final Report
                                      ↑___________|  (retry loop, max 3)
```

---

## Architecture

```
autonomous-agent-system/
├── agents/
│   ├── state.py          # Shared LangGraph TypedDict state
│   ├── base.py           # Abstract BaseAgent (timing, logging, token tracking)
│   ├── planner.py        # Decomposes task into ordered subtasks (JSON output)
│   ├── researcher.py     # Web search + vector memory + LLM summarisation
│   ├── coder.py          # Generates executable Python code
│   ├── executor.py       # Runs code in Docker / subprocess sandbox
│   ├── critic.py         # Evaluates output, triggers retries or human review
│   └── reporter.py       # Compiles final Markdown report with metadata
│
├── tools/
│   ├── python_executor.py  # Docker + subprocess sandbox with artefact capture
│   ├── web_search.py       # DuckDuckGo search wrapper
│   ├── vector_search.py    # ChromaDB semantic search (short-term memory)
│   └── dataset_loader.py   # CSV/JSON/URL/synthetic dataset loader
│
├── memory/
│   └── vector_store.py     # Long-term ChromaDB + Sentence Transformers store
│
├── orchestration/
│   └── workflow_graph.py   # LangGraph StateGraph with conditional retry loops
│
├── evaluation/
│   └── metrics.py          # Task metrics, Prometheus counters, JSONL logging
│
├── api/
│   └── main.py             # FastAPI: POST /task, GET /status, GET /result, …
│
├── dashboard/
│   ├── index.html          # Real-time monitoring UI (dark theme)
│   └── routes.py           # Mounts dashboard at GET /dashboard
│
├── infra/
│   ├── Dockerfile          # Main application image
│   ├── Dockerfile.sandbox  # Minimal Python sandbox image
│   └── docker-compose.yml  # Full stack deployment
│
├── tests/
│   ├── test_agents.py      # Unit tests for all agents and tools
│   └── test_api.py         # FastAPI endpoint integration tests
│
├── example_task.py         # CLI demo — submits a task and streams progress
├── requirements.txt
└── .env.example
```

### Agent Roles

| Agent | LLM Model | Responsibility |
|---|---|---|
| **Planner** | llama3-70b | Breaks task into 5–8 ordered subtasks (JSON) |
| **Researcher** | mixtral-8x7b | Web search + vector memory + summarisation |
| **Coder** | llama3-70b | Generates self-contained Python code |
| **Executor** | — | Runs code in Docker/subprocess, captures artefacts |
| **Critic** | llama3-70b | Evaluates output; triggers retry or human review |
| **Reporter** | llama3-70b | Compiles Markdown report with insights & metadata |

### Workflow Graph

```
START
  │
  ▼
Planner ──(fail)──► END
  │
  ▼
Researcher
  │
  ▼
Coder ◄──────────────────────────────┐
  │                                   │
  ▼                                   │
Executor                              │
  │                                   │  retry (up to 3x)
  ▼                                   │
Critic ──(fail)────────────────────►──┘
  │
  ├──(human_review)──► END (awaiting_human)
  │
  ▼ (pass)
Reporter
  │
  ▼
END (complete)
```

### Memory System

- **Short-term**: LangGraph `AgentState` TypedDict flows through the graph per-task
- **Long-term**: ChromaDB vector store with `all-MiniLM-L6-v2` embeddings
  - Research summaries stored and retrieved across tasks
  - Namespaced by collection (`global_memory` / task-scoped)

### Code Execution Sandbox

Two modes (auto-selected):

| Mode | Isolation | Requirements |
|---|---|---|
| Docker | Full (no network, memory-limited, separate user) | Docker daemon |
| Subprocess | Process-level (timeout enforced) | Python 3.11 |

All generated files are written to `/tmp/artifacts/` and copied to `artifacts/{task_id}/`.

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo>
cd autonomous-agent-system
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

Get your free Groq API key at: https://console.groq.com/keys

### 3. Run the API server

```bash
PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts at `http://localhost:8000`.

### 4. Open the dashboard

Navigate to: **http://localhost:8000/dashboard**

### 5. Run the example task

```bash
python example_task.py
```

Or with a custom task:

```bash
python example_task.py --task "Research Bitcoin price trends, analyse volatility patterns, generate visualisations, and write a report"
```

---

## API Reference

### Submit a Task

```bash
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Analyse global renewable energy adoption trends 2015-2024. Generate synthetic datasets, perform EDA, create visualisations (line charts, bar charts, heatmaps), identify key growth markets, and produce a structured report with insights."
  }'
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Task accepted and workflow started",
  "submitted_at": "2024-01-15T10:30:00"
}
```

### Poll Status

```bash
curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

```json
{
  "task_id": "550e8400-...",
  "status": "running",
  "workflow_status": "running",
  "current_step": "CoderAgent",
  "retry_count": 0,
  "subtasks": ["Research topic", "Load data", "Analyse data", "Create charts", "Write report"],
  "human_confirmation_needed": false,
  "elapsed_s": 12.4,
  "error": null
}
```

### Get Result

```bash
curl http://localhost:8000/result/550e8400-e29b-41d4-a716-446655440000
```

```json
{
  "task_id": "550e8400-...",
  "status": "complete",
  "report": "# Renewable Energy Analysis\n\n## Executive Summary\n...",
  "report_path": "./artifacts/550e8400.../report.md",
  "artifacts": ["./artifacts/550e8400.../chart_timeseries.png"],
  "token_usage": {"PlannerAgent": 312, "ResearchAgent": 1205, "CoderAgent": 2100, ...},
  "step_timings": {"PlannerAgent": 1.2, "ResearchAgent": 4.5, "CoderAgent": 3.1, ...},
  "sources": ["https://example.com/energy-report"]
}
```

### Human-in-the-Loop Confirmation

When the Critic escalates after max retries, the workflow pauses:

```bash
# Proceed
curl -X POST http://localhost:8000/confirm/550e8400-... \
  -H "Content-Type: application/json" \
  -d '{"action": "proceed", "feedback": "Please simplify the visualisation code"}'

# Abort
curl -X POST http://localhost:8000/confirm/550e8400-... \
  -d '{"action": "abort"}'
```

### System Metrics

```bash
curl http://localhost:8000/metrics
```

```json
{
  "total_tasks": 42,
  "successful_tasks": 38,
  "failed_tasks": 4,
  "task_success_rate": 0.9048,
  "execution_failure_rate": 0.0952,
  "total_tokens_used": 1250000,
  "avg_tokens_per_task": 29761,
  "avg_latency_s": 47.3,
  "total_retries": 9
}
```

### Other Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/tasks` | List all tasks |
| `GET` | `/dashboard` | Web UI |
| `GET` | `/metrics/{task_id}` | Per-task metrics |
| `GET` | `/artifacts/{task_id}/{file}` | Download artefact |
| `DELETE` | `/task/{task_id}` | Remove completed task |

---

## Docker Deployment

### Build and run

```bash
cd infra
docker-compose up --build
```

### Build the sandbox image (for Docker code execution)

```bash
docker build -f infra/Dockerfile.sandbox -t amas-sandbox:latest .
# Then set USE_DOCKER=true in .env
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/test_agents.py -v

# API tests only
pytest tests/test_api.py -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | **required** | Groq API key |
| `GROQ_MODEL_PRIMARY` | `llama3-70b-8192` | Main reasoning model |
| `GROQ_MODEL_FAST` | `mixtral-8x7b-32768` | Speed-optimised tasks |
| `GROQ_MODEL_CODE` | `llama3-70b-8192` | Code generation |
| `GROQ_TEMPERATURE` | `0.1` | LLM temperature |
| `MAX_RETRIES` | `3` | Critic retry limit |
| `CONFIDENCE_THRESHOLD` | `0.6` | Below this → human review |
| `USE_DOCKER` | `false` | Enable Docker sandbox |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Vector DB path |
| `METRICS_ENABLED` | `true` | Prometheus metrics |
| `PROMETHEUS_PORT` | `9090` | Prometheus port |

---

## Evaluation Metrics

The system tracks and persists the following metrics to `logs/metrics.jsonl`:

| Metric | Description |
|---|---|
| Task success rate | `successful / total` |
| Execution failure rate | `exec_failures / total_tasks` |
| Token usage | Per-agent and total, per task |
| Task completion latency | Wall-clock time from submit to complete |
| Retry count | How many Critic→Coder cycles occurred |
| Artifact count | Files generated per task |

Prometheus metrics are exposed on `http://localhost:9090/metrics` when enabled.

---

## Example Workflow Trace

```
📋 Task: Analyse global EV adoption trends…

  📐  PlannerAgent          → 6 subtasks in 1.2s, 312 tokens
  🔍  ResearchAgent         → 5 web results, 3 memory hits, summary in 4.5s
  💻  CoderAgent            → 187 lines of Python in 3.1s
  ⚙️   ExecutorAgent         → success, 2 artifacts (CSV + PNG) in 8.2s
  🔬  CriticAgent           → verdict=pass, confidence=0.87 in 2.3s
  📄  ReporterAgent         → 1,240-word report saved in 3.8s

✅ Complete in 23.1s — 4,850 tokens — artifacts/task_id/
```

---

## Design Decisions

**Why LangGraph?**  
LangGraph provides explicit, inspectable state machines. The retry loop (Critic → Coder → Executor → Critic) is a first-class graph construct, not fragile recursive logic.

**Why Groq?**  
Groq's inference hardware delivers sub-second token generation, which is critical for multi-agent loops where latency compounds across 6+ LLM calls per task.

**Why ChromaDB?**  
Zero-config, file-persisted vector store that runs in-process. No additional infrastructure needed for development; can swap to Weaviate/Pinecone for production.

**Why subprocess fallback?**  
Not all environments have Docker. The subprocess fallback ensures the system runs anywhere Python 3.11 is available, while the Docker path provides production-grade isolation.
