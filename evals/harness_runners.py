from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from evals.discover import Task
from shared.paths import CONTEXT_DIR, REPO_ROOT
from shared.results import AgentResult


HARNESSES = ("deepagents", "pydantic-ai", "pi-durable")


def run_harness(
    harness: str,
    task: Task,
    workspace: Path,
    *,
    model: str,
    max_steps: int,
) -> AgentResult:
    if harness == "deepagents":
        return _run_python_module(
            "harnesses.deepagents.run",
            harness_label="deepagents",
            task=task,
            workspace=workspace,
            model=model,
            max_steps=max_steps,
        )
    if harness == "pydantic-ai":
        return _run_python_module(
            "harnesses.pydantic_ai.run",
            harness_label="pydantic-ai",
            task=task,
            workspace=workspace,
            model=model,
            max_steps=max_steps,
        )
    if harness == "pi-durable":
        return _run_pi_durable(task, workspace, model=model, max_steps=max_steps)
    raise ValueError(f"Unknown harness: {harness}")


def _run_python_module(
    module: str,
    *,
    harness_label: str,
    task: Task,
    workspace: Path,
    model: str,
    max_steps: int,
) -> AgentResult:
    cmd = [
        sys.executable,
        "-m",
        module,
        "--workspace",
        str(workspace),
        "--issue",
        str(task.issue_path),
        "--task-dir",
        str(task.path),
        "--task-id",
        task.id,
        "--context-dir",
        str(CONTEXT_DIR),
        "--model",
        model,
        "--max-steps",
        str(max_steps),
        "--json",
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        timeout=300,
    )
    return _parse_result(proc, harness_label=harness_label, task_id=task.id, model=model)


def _run_pi_durable(
    task: Task,
    workspace: Path,
    *,
    model: str,
    max_steps: int,
) -> AgentResult:
    ts_entry = REPO_ROOT / "harnesses" / "pi-durable" / "src" / "run.ts"
    cmd = [
        "pnpm",
        "exec",
        "tsx",
        str(ts_entry),
        "--workspace",
        str(workspace),
        "--issue",
        str(task.issue_path),
        "--task-dir",
        str(task.path),
        "--task-id",
        task.id,
        "--context-dir",
        str(CONTEXT_DIR),
        "--model",
        model,
        "--max-steps",
        str(max_steps),
        "--json",
    ]
    env = os.environ.copy()
    # Prefer the same interpreter uv/evals is using so pytest is importable.
    env.setdefault("HARNESS_PYTHON", sys.executable)
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT / "harnesses" / "pi-durable",
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    return _parse_result(proc, harness_label="pi-durable", task_id=task.id, model=model)


def _parse_result(
    proc: subprocess.CompletedProcess[str],
    *,
    harness_label: str,
    task_id: str,
    model: str,
) -> AgentResult:
    raw = (proc.stdout or "").strip()
    try:
        # Harnesses may print logs; take the last JSON object.
        data = _extract_json(raw)
        return AgentResult(**{k: data.get(k) for k in AgentResult.__dataclass_fields__})
    except Exception as exc:  # noqa: BLE001
        return AgentResult(
            harness=harness_label,
            task_id=task_id,
            passed=False,
            steps=0,
            wall_time_ms=0.0,
            model=model,
            message="",
            error=f"failed to parse harness output: {exc}; stderr={proc.stderr!r}; stdout={raw[:500]!r}",
        )


def _extract_json(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("empty stdout")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.rfind("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        return json.loads(text[start : end + 1])
