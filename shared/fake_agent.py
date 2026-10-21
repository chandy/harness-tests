from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from shared.results import AgentResult
from shared.tools import WorkspaceTools


def load_fake_plan(task_dir: Path) -> list[dict[str, Any]]:
    plan_path = task_dir / "fake_plan.json"
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"Invalid fake plan: {plan_path}")
    return steps


def run_fake_agent(
    *,
    harness: str,
    task_id: str,
    task_dir: Path,
    workspace: Path,
    max_steps: int = 20,
) -> AgentResult:
    """Deterministic scripted agent for CI / no-API-key runs."""
    tools = WorkspaceTools(root=workspace)
    plan = load_fake_plan(task_dir)
    started = time.perf_counter()
    steps = 0
    message = ""
    error: str | None = None

    try:
        for step in plan:
            if steps >= max_steps:
                error = f"Exceeded max_steps={max_steps}"
                break
            steps += 1
            if "done" in step:
                message = str(step["done"])
                break
            tool = step["tool"]
            args = dict(step.get("args") or {})
            tools.dispatch(tool, args)
        else:
            message = "Plan finished without an explicit done step"
    except Exception as exc:  # noqa: BLE001 - surface to evals
        error = str(exc)

    wall_ms = (time.perf_counter() - started) * 1000
    grade = _grade_workspace(workspace)
    passed = grade == 0 and error is None
    if not message:
        message = "Tests passed" if passed else "Tests failed or agent error"
    return AgentResult(
        harness=harness,
        task_id=task_id,
        passed=passed,
        steps=steps,
        wall_time_ms=round(wall_ms, 2),
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        model="fake",
        message=message,
        error=error,
        tool_calls=tools.call_log,
    )


def _grade_workspace(workspace: Path) -> int:
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode
