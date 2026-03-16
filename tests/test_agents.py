"""
Unit tests for agents and tools.
Run with: pytest tests/ -v
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Test helpers ───────────────────────────────────────────────────────────────

def make_base_state(**overrides):
    state = {
        "task_id": "test-123",
        "original_task": "Analyse sales data and create a report",
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
    state.update(overrides)
    return state


# ── LLM wrapper mock ──────────────────────────────────────────────────────────

def mock_llm_complete(content: str):
    llm = MagicMock()
    llm.complete.return_value = {"content": content, "usage": {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50, "latency_s": 0.5}}
    llm.complete_json.return_value = {"content": content, "usage": {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50, "latency_s": 0.5}}
    llm.total_tokens_used = 100
    llm.reset_token_counter = MagicMock()
    return llm


# ── Planner tests ─────────────────────────────────────────────────────────────

class TestPlannerAgent:
    def test_planner_produces_subtasks(self):
        from agents.planner import PlannerAgent

        planner = PlannerAgent.__new__(PlannerAgent)
        planner.name = "PlannerAgent"
        planner.logger = MagicMock()
        planner.llm = mock_llm_complete(
            json.dumps({"tasks": ["Research topic", "Load data", "Analyse data", "Create charts", "Write report"]})
        )

        state = make_base_state()
        result = planner.run(state)

        assert "subtasks" in result
        assert len(result["subtasks"]) == 5
        assert result["workflow_status"] == "running"

    def test_planner_handles_bad_json(self):
        from agents.planner import PlannerAgent

        planner = PlannerAgent.__new__(PlannerAgent)
        planner.name = "PlannerAgent"
        planner.logger = MagicMock()
        planner.llm = mock_llm_complete("NOT VALID JSON AT ALL")

        state = make_base_state()
        result = planner.run(state)

        # Should produce fallback subtasks
        assert "subtasks" in result
        assert len(result["subtasks"]) > 0

    def test_planner_empty_task(self):
        from agents.planner import PlannerAgent

        planner = PlannerAgent.__new__(PlannerAgent)
        planner.name = "PlannerAgent"
        planner.logger = MagicMock()
        planner.llm = MagicMock()

        state = make_base_state(original_task="")
        result = planner.run(state)

        assert result["workflow_status"] == "failed"


# ── Coder tests ────────────────────────────────────────────────────────────────

class TestCoderAgent:
    def test_coder_generates_code(self):
        from agents.coder import CoderAgent

        coder = CoderAgent.__new__(CoderAgent)
        coder.name = "CoderAgent"
        coder.logger = MagicMock()
        coder.llm = mock_llm_complete("import pandas as pd\nprint('hello')")

        state = make_base_state(
            subtasks=["Analyse sales data"],
            current_subtask_index=0,
        )
        result = coder.run(state)

        assert "generated_code" in result
        assert "import pandas" in result["generated_code"]

    def test_coder_strips_markdown_fences(self):
        from agents.coder import _strip_fences

        raw = "```python\nprint('hello')\n```"
        assert _strip_fences(raw) == "print('hello')"

        raw2 = "```\nprint('hello')\n```"
        assert _strip_fences(raw2) == "print('hello')"

    def test_coder_includes_retry_feedback(self):
        from agents.coder import CoderAgent

        captured = {}

        coder = CoderAgent.__new__(CoderAgent)
        coder.name = "CoderAgent"
        coder.logger = MagicMock()

        def capture_complete(prompt, **kwargs):
            captured["prompt"] = prompt
            return {"content": "print('fixed')", "usage": {"total_tokens": 50}}

        coder.llm = MagicMock()
        coder.llm.complete.side_effect = capture_complete

        state = make_base_state(
            subtasks=["Fix bug"],
            critic_feedback="NameError on line 5",
            retry_count=1,
        )
        coder.run(state)
        assert "NameError on line 5" in captured.get("prompt", "")


# ── Critic tests ──────────────────────────────────────────────────────────────

class TestCriticAgent:
    def test_critic_passes_good_output(self):
        from agents.critic import CriticAgent

        critic = CriticAgent.__new__(CriticAgent)
        critic.name = "CriticAgent"
        critic.logger = MagicMock()
        critic.llm = mock_llm_complete(
            json.dumps({"verdict": "pass", "confidence": 0.9, "issues": [], "feedback": "", "summary": "Good output"})
        )

        state = make_base_state(
            execution_status="success",
            execution_stdout='{"status": "success", "files": [], "insights": ["Revenue grew 15%"]}',
            execution_artifacts=["report.png"],
        )
        result = critic.run(state)
        assert result["critic_verdict"] == "pass"

    def test_critic_fails_execution_error(self):
        from agents.critic import CriticAgent

        critic = CriticAgent.__new__(CriticAgent)
        critic.name = "CriticAgent"
        critic.logger = MagicMock()
        critic.llm = MagicMock()

        state = make_base_state(
            execution_status="failure",
            execution_stderr="NameError: name 'df' is not defined",
            retry_count=0,
        )
        result = critic.run(state)
        assert result["critic_verdict"] == "fail"
        assert result["retry_count"] == 1

    def test_critic_escalates_after_max_retries(self):
        from agents.critic import CriticAgent
        from config.settings import settings

        critic = CriticAgent.__new__(CriticAgent)
        critic.name = "CriticAgent"
        critic.logger = MagicMock()
        critic.llm = MagicMock()

        state = make_base_state(
            execution_status="failure",
            execution_stderr="Error",
            retry_count=settings.MAX_RETRIES,
        )
        result = critic.run(state)
        assert result["critic_verdict"] == "human_review"
        assert result["workflow_status"] == "awaiting_human"


# ── Executor (tool) tests ─────────────────────────────────────────────────────

class TestPythonExecutor:
    def test_execute_simple_code(self):
        from tools.python_executor import PythonExecutorTool

        tool = PythonExecutorTool()
        tool.use_docker = False  # force subprocess

        result = tool.execute("print('hello world')", task_id="test-exec-1")

        assert result["exit_code"] == 0
        assert "hello world" in result["stdout"]
        assert result["stderr"] == ""

    def test_execute_error_code(self):
        from tools.python_executor import PythonExecutorTool

        tool = PythonExecutorTool()
        tool.use_docker = False

        result = tool.execute("raise ValueError('intentional error')", task_id="test-exec-2")

        assert result["exit_code"] != 0
        assert "ValueError" in result["stderr"]

    def test_execute_file_creation(self):
        import os
        from tools.python_executor import PythonExecutorTool
        from config.settings import settings

        tool = PythonExecutorTool()
        tool.use_docker = False

        code = """
import pathlib, json
p = pathlib.Path('/tmp/amas_test-exec-3')
p.mkdir(parents=True, exist_ok=True)
(p / 'output.txt').write_text('test output')
"""
        result = tool.execute(code, task_id="test-exec-3")
        assert result["exit_code"] == 0


# ── Web search tests ──────────────────────────────────────────────────────────

class TestWebSearch:
    def test_search_returns_list(self):
        from tools.web_search import WebSearchTool

        tool = WebSearchTool()
        # Mock the underlying ddg call
        with patch.object(tool, '_ddg_search', return_value=[
            {"title": "Test Result", "snippet": "Test snippet", "url": "https://example.com"}
        ]):
            results = tool.search("test query")
            assert isinstance(results, list)
            assert results[0]["title"] == "Test Result"

    def test_search_handles_failure_gracefully(self):
        from tools.web_search import WebSearchTool

        tool = WebSearchTool()
        with patch.object(tool, '_ddg_search', side_effect=Exception("network error")):
            results = tool.search("test query")
            assert results == []


# ── Dataset loader tests ──────────────────────────────────────────────────────

class TestDatasetLoader:
    def test_load_synthetic_sales(self):
        from tools.dataset_loader import DatasetLoaderTool

        tool = DatasetLoaderTool()
        result = tool.load("synthetic:sales")

        assert result["dataframe"] is not None
        assert result["shape"][0] > 0
        assert "revenue" in result["columns"]

    def test_load_synthetic_timeseries(self):
        from tools.dataset_loader import DatasetLoaderTool

        tool = DatasetLoaderTool()
        result = tool.load("synthetic:timeseries")

        assert result["shape"][1] == 2
        assert "date" in result["columns"]
        assert "value" in result["columns"]


# ── Metrics tests ─────────────────────────────────────────────────────────────

class TestMetrics:
    def test_metrics_lifecycle(self):
        from evaluation.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.start_task("task-1", "Test task")
        collector.finish_task("task-1", {
            "workflow_status": "complete",
            "token_usage": {"PlannerAgent": 100},
            "step_timings": {"PlannerAgent": 1.0},
            "retry_count": 0,
            "subtasks": ["a", "b"],
            "execution_artifacts": ["file.png"],
            "execution_status": "success",
            "error_message": "",
        })

        m = collector.get_task("task-1")
        assert m is not None
        assert m["success"] is True
        assert m["total_tokens"] == 100

        agg = collector.get_aggregates()
        assert agg["total_tasks"] == 1
        assert agg["successful_tasks"] == 1
        assert agg["task_success_rate"] == 1.0


# ── Integration smoke test ────────────────────────────────────────────────────

class TestWorkflowIntegration:
    """Smoke test the full workflow graph construction."""

    def test_workflow_builds_without_error(self):
        """Ensure the LangGraph graph compiles without an API key."""
        with patch("config.llm.build_llm") as mock_build:
            mock_build.return_value = MagicMock()
            from orchestration.workflow_graph import build_workflow
            graph = build_workflow()
            assert graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
