"""
FastAPI endpoint tests using httpx TestClient.
"""
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def client():
    """Create a test client with mocked workflow execution."""
    with patch("orchestration.workflow_graph.get_workflow") as mock_wf, \
         patch("evaluation.metrics.get_metrics") as mock_metrics:

        mock_metrics.return_value = MagicMock(
            start_task=MagicMock(),
            finish_task=MagicMock(),
            get_task=MagicMock(return_value={"latency_s": 2.5}),
            get_aggregates=MagicMock(return_value={
                "total_tasks": 5, "successful_tasks": 4, "failed_tasks": 1,
                "task_success_rate": 0.8, "execution_failure_rate": 0.1,
                "total_tokens_used": 50000, "avg_tokens_per_task": 10000,
                "avg_latency_s": 12.5, "total_retries": 2,
            }),
            get_all_tasks=MagicMock(return_value=[]),
        )

        from api.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "active_tasks" in data


def test_submit_task(client):
    r = client.post("/task", json={"task": "Analyse renewable energy trends and produce a report"})
    assert r.status_code == 202
    data = r.json()
    assert "task_id" in data
    assert data["status"] == "accepted"


def test_submit_task_too_short(client):
    r = client.post("/task", json={"task": "short"})
    assert r.status_code == 422  # Validation error


def test_status_not_found(client):
    r = client.get("/status/nonexistent-task-id")
    assert r.status_code == 404


def test_result_not_found(client):
    r = client.get("/result/nonexistent-task-id")
    assert r.status_code == 404


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "total_tasks" in data
    assert "task_success_rate" in data


def test_list_tasks_empty(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    data = r.json()
    assert "tasks" in data
    assert "total" in data


def test_submit_and_status_flow(client):
    """Test that submitting a task creates a trackable status."""
    r = client.post("/task", json={"task": "Research AI trends and generate a comprehensive analysis report"})
    assert r.status_code == 202
    task_id = r.json()["task_id"]

    # Status should be findable immediately
    sr = client.get(f"/status/{task_id}")
    assert sr.status_code == 200
    status_data = sr.json()
    assert status_data["task_id"] == task_id


def test_dashboard_serves(client):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Autonomous" in r.text


def test_delete_running_task_rejected(client):
    """Cannot delete a running task."""
    r = client.post("/task", json={"task": "Research quantum computing breakthroughs and write a detailed report"})
    task_id = r.json()["task_id"]
    dr = client.delete(f"/task/{task_id}")
    # Running task should be rejected
    assert dr.status_code in (400, 404)
