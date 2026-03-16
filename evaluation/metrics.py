"""
Evaluation & Metrics System
────────────────────────────
Tracks, stores, and exposes operational metrics for the agent workflow:

  - Task success / failure rates
  - Execution failure rates
  - Token usage per agent and globally
  - Task completion latency
  - Retry statistics
  - Confidence score distribution

Storage: JSON file (lightweight) + optional Prometheus counters.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskMetrics:
    task_id: str
    original_task: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # Outcomes
    status: str = "running"          # running | complete | failed | awaiting_human
    success: bool = False
    error_message: str = ""

    # Agent-level
    token_usage: dict[str, int] = field(default_factory=dict)
    step_timings: dict[str, float] = field(default_factory=dict)
    retry_count: int = 0
    subtask_count: int = 0

    # Execution
    execution_attempts: int = 0
    execution_failures: int = 0
    artifacts_count: int = 0

    @property
    def latency_s(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 3)

    @property
    def total_tokens(self) -> int:
        return sum(self.token_usage.values())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["latency_s"] = self.latency_s
        d["total_tokens"] = self.total_tokens
        d["timestamp"] = datetime.utcfromtimestamp(self.start_time).isoformat()
        return d


class MetricsCollector:
    """
    Thread-safe metrics collector.

    Persists individual task records to JSONL and maintains
    rolling aggregate counters in memory.
    """

    def __init__(self) -> None:
        from config.settings import settings
        self._lock = threading.Lock()
        self._records: dict[str, TaskMetrics] = {}
        self._log_path = settings.LOGS_DIR / "metrics.jsonl"
        self._agg = _Aggregates()
        self._init_prometheus()

    # ── Task lifecycle ─────────────────────────────────────────────────────────

    def start_task(self, task_id: str, task_text: str) -> None:
        with self._lock:
            self._records[task_id] = TaskMetrics(
                task_id=task_id, original_task=task_text
            )
        logger.debug("Metrics: started task %s", task_id)

    def update_task(self, task_id: str, **kwargs: Any) -> None:
        """Update any field(s) on a TaskMetrics record."""
        with self._lock:
            rec = self._records.get(task_id)
            if rec is None:
                return
            for k, v in kwargs.items():
                if hasattr(rec, k):
                    setattr(rec, k, v)

    def finish_task(self, task_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            rec = self._records.get(task_id)
            if rec is None:
                return

            rec.end_time = time.time()
            rec.status = state.get("workflow_status", "unknown")
            rec.success = rec.status == "complete"
            rec.error_message = state.get("error_message", "")
            rec.token_usage = state.get("token_usage", {})
            rec.step_timings = state.get("step_timings", {})
            rec.retry_count = state.get("retry_count", 0)
            rec.subtask_count = len(state.get("subtasks", []))
            rec.artifacts_count = len(state.get("execution_artifacts", []))

            # Execution counters
            if state.get("execution_status") == "failure":
                rec.execution_failures += 1
            rec.execution_attempts = rec.retry_count + 1

            # Update aggregates
            self._agg.total_tasks += 1
            if rec.success:
                self._agg.successful_tasks += 1
            else:
                self._agg.failed_tasks += 1
            self._agg.total_tokens += rec.total_tokens
            self._agg.total_latency += rec.latency_s
            self._agg.execution_failures += rec.execution_failures
            self._agg.total_retries += rec.retry_count

            self._flush(rec)

            # Prometheus
            if self._prom_ok:
                self._prom_task_total.labels(status=rec.status).inc()
                self._prom_tokens.observe(rec.total_tokens)
                self._prom_latency.observe(rec.latency_s)

    # ── Query ──────────────────────────────────────────────────────────────────

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            rec = self._records.get(task_id)
            return rec.to_dict() if rec else None

    def get_aggregates(self) -> dict[str, Any]:
        with self._lock:
            agg = self._agg
            success_rate = (
                agg.successful_tasks / agg.total_tasks if agg.total_tasks else 0.0
            )
            avg_latency = (
                agg.total_latency / agg.total_tasks if agg.total_tasks else 0.0
            )
            exec_failure_rate = (
                agg.execution_failures / max(agg.total_tasks, 1)
            )
            return {
                "total_tasks": agg.total_tasks,
                "successful_tasks": agg.successful_tasks,
                "failed_tasks": agg.failed_tasks,
                "task_success_rate": round(success_rate, 4),
                "execution_failure_rate": round(exec_failure_rate, 4),
                "total_tokens_used": agg.total_tokens,
                "avg_tokens_per_task": round(
                    agg.total_tokens / max(agg.total_tasks, 1), 1
                ),
                "avg_latency_s": round(avg_latency, 3),
                "total_retries": agg.total_retries,
            }

    def get_all_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._records.values()]

    # ── Internal ───────────────────────────────────────────────────────────────

    def _flush(self, rec: TaskMetrics) -> None:
        try:
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict()) + "\n")
        except Exception as exc:
            logger.warning("Metrics flush failed: %s", exc)

    def _init_prometheus(self) -> None:
        self._prom_ok = False
        try:
            from prometheus_client import Counter, Histogram, start_http_server
            from config.settings import settings

            if not settings.METRICS_ENABLED:
                return

            self._prom_task_total = Counter(
                "agent_tasks_total", "Total tasks", ["status"]
            )
            self._prom_tokens = Histogram(
                "agent_tokens_per_task", "Token usage per task",
                buckets=[100, 500, 1000, 2500, 5000, 10000, 25000],
            )
            self._prom_latency = Histogram(
                "agent_task_latency_seconds", "Task latency",
                buckets=[1, 5, 15, 30, 60, 120, 300],
            )
            start_http_server(settings.PROMETHEUS_PORT)
            self._prom_ok = True
            logger.info("Prometheus metrics on port %d", settings.PROMETHEUS_PORT)
        except Exception as exc:
            logger.debug("Prometheus disabled: %s", exc)


@dataclass
class _Aggregates:
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_tokens: int = 0
    total_latency: float = 0.0
    execution_failures: int = 0
    total_retries: int = 0


# Module-level singleton
_collector: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
