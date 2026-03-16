"""
Python Executor Tool
────────────────────
Runs generated Python code safely via subprocess.
Captures stdout, stderr, exit code, and any written files.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PREAMBLE = """\
import os, sys, pathlib, json, traceback
_ARTIFACTS = pathlib.Path('{artifacts_dir}')
_ARTIFACTS.mkdir(parents=True, exist_ok=True)

"""


class PythonExecutorTool:
    def __init__(self) -> None:
        from config.settings import settings
        self.use_docker = False   # always subprocess on Railway
        self.timeout = settings.DOCKER_EXECUTION_TIMEOUT

    def execute(self, code: str, task_id: str = "task") -> dict[str, Any]:
        start = time.perf_counter()
        result = self._subprocess_execute(code, task_id)
        result["duration_s"] = round(time.perf_counter() - start, 3)
        return result

    def _subprocess_execute(self, code: str, task_id: str) -> dict[str, Any]:
        from config.settings import settings

        # Use /tmp which is always writable
        artifacts_dir = Path(tempfile.gettempdir()) / f"amas_{task_id}"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        full_code = _PREAMBLE.format(artifacts_dir=str(artifacts_dir)) + code

        # Write to temp script file
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(full_code)
            tmp.flush()
            tmp.close()

            # Use sys.executable so we always use the same Python as the app
            proc = subprocess.run(
                [sys.executable, tmp.name],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, "MPLBACKEND": "Agg"},  # non-interactive matplotlib
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            exit_code = proc.returncode

            if exit_code != 0:
                logger.warning("Execution failed (exit=%d): %s", exit_code, stderr[:300])
            else:
                logger.info("Execution succeeded in task %s", task_id)

        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = f"Execution timed out after {self.timeout}s"
            exit_code = 1
        except Exception as exc:
            stdout = ""
            stderr = f"Executor error: {exc}"
            exit_code = 1
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

        artifacts = _collect_artifacts(artifacts_dir, task_id)
        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "artifacts": artifacts,
        }


def _collect_artifacts(artifacts_dir: Path, task_id: str) -> list[str]:
    from config.settings import settings

    dest_dir = settings.ARTIFACTS_DIR / task_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    if not artifacts_dir.exists():
        return paths

    for f in artifacts_dir.iterdir():
        if f.is_file():
            dest = dest_dir / f.name
            try:
                shutil.copy2(f, dest)
                paths.append(str(dest))
            except Exception as exc:
                logger.warning("Could not copy artifact %s: %s", f, exc)

    return paths