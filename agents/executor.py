"""
Python Executor Tool
────────────────────
Runs generated Python code via subprocess.
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

# Injected at the top of every generated script
_PREAMBLE = """\
import matplotlib
matplotlib.use("Agg")
import os, sys, pathlib, json, traceback

_ARTIFACTS = pathlib.Path('{artifacts_dir}')
_ARTIFACTS.mkdir(parents=True, exist_ok=True)
print(f"[executor] artifacts dir: {{_ARTIFACTS}}", flush=True)

"""


class PythonExecutorTool:
    def __init__(self) -> None:
        from config.settings import settings
        self.timeout = settings.DOCKER_EXECUTION_TIMEOUT

    def execute(self, code: str, task_id: str = "task") -> dict[str, Any]:
        start = time.perf_counter()

        # Always use a fresh temp dir scoped to this task
        artifacts_dir = Path(tempfile.gettempdir()) / f"amas_{task_id}"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        full_code = _PREAMBLE.format(artifacts_dir=str(artifacts_dir)) + _patch_code(code, artifacts_dir)

        result = self._run(full_code, task_id, artifacts_dir)
        result["duration_s"] = round(time.perf_counter() - start, 3)

        logger.info(
            "Executor: exit=%d stdout=%d chars stderr=%d chars artifacts=%s",
            result["exit_code"],
            len(result.get("stdout", "")),
            len(result.get("stderr", "")),
            result.get("artifacts", []),
        )
        return result

    def _run(self, code: str, task_id: str, artifacts_dir: Path) -> dict[str, Any]:
        # Write script to temp file
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(code)
            tmp.flush()
            tmp.close()

            proc = subprocess.run(
                [sys.executable, tmp.name],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={
                    **os.environ,
                    "MPLBACKEND": "Agg",
                    "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                },
            )
            stdout   = proc.stdout or ""
            stderr   = proc.stderr or ""
            exit_code = proc.returncode

        except subprocess.TimeoutExpired:
            stdout    = ""
            stderr    = f"Timed out after {self.timeout}s"
            exit_code = 1
        except Exception as exc:
            stdout    = ""
            stderr    = f"Executor error: {exc}"
            exit_code = 1
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

        artifacts = self._collect(artifacts_dir, task_id)
        return {
            "exit_code":  exit_code,
            "stdout":     stdout,
            "stderr":     stderr,
            "artifacts":  artifacts,
        }

    def _collect(self, src: Path, task_id: str) -> list[str]:
        """
        Copy files from the temp artifacts dir into the persistent artifacts dir.
        Returns list of destination paths.
        """
        try:
            from config.settings import settings
            dest_root = settings.ARTIFACTS_DIR / task_id
        except Exception:
            dest_root = Path(tempfile.gettempdir()) / "artifacts" / task_id

        try:
            dest_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create artifacts dest dir: %s", exc)
            return []

        paths: list[str] = []

        if not src.exists():
            logger.warning("Artifacts source dir does not exist: %s", src)
            return paths

        files = list(src.iterdir())
        logger.info("Artifacts source contains %d file(s): %s", len(files), [f.name for f in files])

        for f in files:
            if f.is_file():
                dest = dest_root / f.name
                try:
                    shutil.copy2(f, dest)
                    paths.append(str(dest))
                    logger.info("Artifact copied: %s → %s", f.name, dest)
                except Exception as exc:
                    logger.warning("Could not copy %s: %s", f.name, exc)

        return paths


def _patch_code(code: str, artifacts_dir: Path) -> str:
    """
    Replace any hardcoded /tmp/artifacts paths in the generated code
    with the actual task-scoped artifacts dir.
    Also ensure plt.savefig calls use _ARTIFACTS.
    """
    patched = code

    # Replace hardcoded paths
    patched = patched.replace(
        "pathlib.Path('/tmp/artifacts')",
        f"pathlib.Path('{artifacts_dir}')",
    )
    patched = patched.replace(
        "Path('/tmp/artifacts')",
        f"Path('{artifacts_dir}')",
    )
    patched = patched.replace(
        "'/tmp/artifacts/",
        f"'{artifacts_dir}/",
    )
    patched = patched.replace(
        '"/tmp/artifacts/',
        f'"{artifacts_dir}/',
    )

    # Remove any duplicate matplotlib.use("Agg") since preamble already sets it
    import re
    patched = re.sub(r"^import matplotlib\s*\n", "", patched, flags=re.MULTILINE)
    patched = re.sub(r'^matplotlib\.use\(["\']Agg["\']\)\s*\n', "", patched, flags=re.MULTILINE)

    return patched