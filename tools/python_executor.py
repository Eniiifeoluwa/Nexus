"""
Python Executor Tool
────────────────────
Runs untrusted Python code safely.

Strategy
--------
1. If USE_DOCKER=True and Docker daemon is reachable → Docker container sandbox
2. Otherwise → subprocess with a timeout and a restricted tmp directory

The code is always executed inside /tmp/artifacts/ so any files it writes
are captured as artefacts.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Packages available in the sandbox image (also used for subprocess path)
_ALLOWED_IMPORTS = {
    "pandas", "numpy", "matplotlib", "seaborn",
    "sklearn", "scipy", "json", "os", "pathlib",
    "csv", "math", "random", "datetime", "collections",
    "itertools", "functools", "re", "statistics",
}

_PREAMBLE = """\
import os, pathlib
_ARTIFACTS = pathlib.Path('/tmp/artifacts')
_ARTIFACTS.mkdir(parents=True, exist_ok=True)

"""


class PythonExecutorTool:
    """
    Executes Python code in a sandboxed environment and returns structured results.

    Returns
    -------
    {
        "exit_code": int,
        "stdout": str,
        "stderr": str,
        "artifacts": [list of file paths],
        "duration_s": float,
    }
    """

    def __init__(self) -> None:
        from config.settings import settings
        self.use_docker: bool = settings.USE_DOCKER
        self.timeout: int = settings.DOCKER_EXECUTION_TIMEOUT
        self.image: str = settings.DOCKER_SANDBOX_IMAGE
        self.mem_limit: str = settings.DOCKER_MEMORY_LIMIT

        if self.use_docker:
            self._check_docker()

    # ── Public API ─────────────────────────────────────────────────────────────

    def execute(self, code: str, task_id: str = "task") -> dict[str, Any]:
        full_code = _PREAMBLE + code
        start = time.perf_counter()

        if self.use_docker:
            result = self._docker_execute(full_code, task_id)
        else:
            result = self._subprocess_execute(full_code, task_id)

        result["duration_s"] = round(time.perf_counter() - start, 3)
        return result

    # ── Docker execution ───────────────────────────────────────────────────────

    def _docker_execute(self, code: str, task_id: str) -> dict[str, Any]:
        try:
            import docker  # type: ignore
        except ImportError:
            logger.warning("docker-py not installed; falling back to subprocess")
            return self._subprocess_execute(code, task_id)

        host_artifacts = Path(tempfile.mkdtemp(prefix=f"amas_{task_id}_"))

        try:
            client = docker.from_env()
            container = client.containers.run(
                image=self.image,
                command=["python3", "-c", code],
                volumes={str(host_artifacts): {"bind": "/tmp/artifacts", "mode": "rw"}},
                mem_limit=self.mem_limit,
                network_mode="none",          # no network access
                remove=True,
                stdout=True,
                stderr=True,
                detach=False,
                timeout=self.timeout,
            )
            stdout = container.decode("utf-8") if isinstance(container, bytes) else ""
            stderr = ""
            exit_code = 0
        except Exception as exc:
            logger.exception("Docker execution failed: %s", exc)
            stdout = ""
            stderr = str(exc)
            exit_code = 1

        artifacts = _collect_artifacts(host_artifacts, task_id)
        return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr, "artifacts": artifacts}

    # ── Subprocess execution (fallback) ────────────────────────────────────────

    def _subprocess_execute(self, code: str, task_id: str) -> dict[str, Any]:
        from config.settings import settings

        artifacts_dir = Path("/tmp") / f"amas_{task_id}"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Redirect artifact path to task-specific directory
        patched = code.replace(
            "_ARTIFACTS = pathlib.Path('/tmp/artifacts')",
            f"_ARTIFACTS = pathlib.Path('{artifacts_dir}')",
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(patched)
            script_path = tf.name

        try:
            proc = subprocess.run(
                ["python3", script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = f"Execution timed out after {self.timeout}s"
            exit_code = 1
        except Exception as exc:
            stdout = ""
            stderr = str(exc)
            exit_code = 1
        finally:
            os.unlink(script_path)

        artifacts = _collect_artifacts(artifacts_dir, task_id)
        return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr, "artifacts": artifacts}

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _check_docker(self) -> None:
        try:
            import docker
            docker.from_env().ping()
            logger.info("Docker daemon reachable — sandbox enabled")
        except Exception:
            logger.warning("Docker not available — falling back to subprocess")
            self.use_docker = False


def _collect_artifacts(artifacts_dir: Path, task_id: str) -> list[str]:
    """Copy generated files to the project artifacts directory and return paths."""
    from config.settings import settings

    dest_dir = settings.ARTIFACTS_DIR / task_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    if not artifacts_dir.exists():
        return paths

    for f in artifacts_dir.iterdir():
        if f.is_file():
            dest = dest_dir / f.name
            shutil.copy2(f, dest)
            paths.append(str(dest))

    return paths
