from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.capabilities import LocalWorkspace
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai_harness.coder import Coder

from shared.context_loader import load_issue, load_system_prompt
from shared.model_mode import model_id_for_mode
from shared.results import AgentResult

HARNESS_NAME = "pydantic-ai-harness"


def _translate_plan_step(step: dict[str, Any]) -> dict[str, Any]:
    """Map shared fake_plan tool calls onto Coder's built-in tools."""
    if "done" in step:
        return step
    tool = step["tool"]
    args = dict(step.get("args") or {})
    if tool == "run_tests":
        # Shared contract → Coder `shell`
        return {
            "tool": "shell",
            "args": {"command": f"{sys.executable} -m pytest -q --tb=short"},
        }
    if tool == "edit_file":
        # Shared contract uses old_str/new_str; Coder FileSystem uses old_text/new_text
        if "old_str" in args and "old_text" not in args:
            args["old_text"] = args.pop("old_str")
        if "new_str" in args and "new_text" not in args:
            args["new_text"] = args.pop("new_str")
        return {"tool": "edit_file", "args": args}
    return {"tool": tool, "args": args}


def _plan_function_model(task_dir: Path) -> FunctionModel:
    raw_steps = json.loads((task_dir / "fake_plan.json").read_text(encoding="utf-8"))["steps"]
    plan = [_translate_plan_step(s) for s in raw_steps]
    state = {"i": 0}

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:  # noqa: ARG001
        if state["i"] >= len(plan):
            return ModelResponse(parts=[TextPart("Done.")])
        step = plan[state["i"]]
        state["i"] += 1
        if "done" in step:
            return ModelResponse(parts=[TextPart(str(step["done"]))])
        return ModelResponse(
            parts=[ToolCallPart(step["tool"], dict(step.get("args") or {}))]
        )

    return FunctionModel(fn)


def build_agent(model: Any, *, workspace: Path, instructions: str) -> Agent[None, str]:
    """Agent(model, capabilities=[LocalWorkspace(sandbox), Coder(instructions=...)])."""
    return Agent(
        model,
        capabilities=[
            LocalWorkspace(workspace),
            Coder(
                instructions=instructions,
                # Shared context/ is injected via instructions; skip fixture AGENTS.md discovery.
                repo_context=False,
                # Keep fake/CI runs single-agent; real models can still use subagents if re-enabled.
                sub_agents=True,
                caching=False,
            ),
        ],
    )


def _count_tool_calls(result: Any) -> int:
    n = 0
    for msg in result.all_messages():
        if isinstance(msg, ModelResponse):
            n += sum(1 for part in msg.parts if isinstance(part, ToolCallPart))
    return n


def _grade_passed(workspace: Path) -> bool:
    import subprocess

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode == 0


def run_pydantic_ai_harness(
    *,
    workspace: Path,
    issue_path: Path,
    task_dir: Path,
    task_id: str,
    context_dir: Path | None,
    model_mode: str,
    max_steps: int,
) -> AgentResult:
    system = load_system_prompt(context_dir)
    issue = load_issue(issue_path)
    prompt = (
        f"Issue:\n{issue}\n\n"
        "Investigate the workspace, fix the bug, and verify with "
        f"`{sys.executable} -m pytest -q --tb=short` via the shell tool. "
        f"Prefer at most ~{max_steps} tool rounds. Stop when tests pass."
    )

    if model_mode == "fake":
        model: Any = _plan_function_model(task_dir)
        model_label = "fake-function-model"
    elif model_mode == "openai":
        model_label = f"openai:{model_id_for_mode(model_mode)}"
        model = model_label
    else:
        model_label = f"anthropic:{model_id_for_mode(model_mode)}"
        model = model_label

    agent = build_agent(model, workspace=workspace, instructions=system)
    started = time.perf_counter()
    error: str | None = None
    message = ""
    steps = 0
    tokens_in = tokens_out = None

    try:
        result = agent.run_sync(prompt)
        message = str(result.output)
        steps = _count_tool_calls(result)
        usage = result.usage() if callable(getattr(result, "usage", None)) else getattr(result, "usage", None)
        if usage is not None:
            tokens_in = getattr(usage, "request_tokens", None) or getattr(usage, "input_tokens", None)
            tokens_out = getattr(usage, "response_tokens", None) or getattr(usage, "output_tokens", None)
        if model_mode == "fake":
            tokens_in = tokens_in or 0
            tokens_out = tokens_out or 0
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    wall_ms = (time.perf_counter() - started) * 1000
    passed = _grade_passed(workspace) and error is None
    return AgentResult(
        harness=HARNESS_NAME,
        task_id=task_id,
        passed=passed,
        steps=steps,
        wall_time_ms=round(wall_ms, 2),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=0.0 if model_mode == "fake" else None,
        model=model_label,
        message=message or ("passed" if passed else "failed"),
        error=error,
        tool_calls=[],
    )
