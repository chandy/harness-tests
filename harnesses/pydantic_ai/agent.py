from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from shared.context_loader import load_issue, load_system_prompt
from shared.fake_agent import run_fake_agent
from shared.model_mode import model_id_for_mode
from shared.results import AgentResult
from shared.tools import WorkspaceTools


class Deps:
    def __init__(self, tools: WorkspaceTools):
        self.tools = tools


def build_agent(system_prompt: str, model: str | Any) -> Agent[Deps, str]:
    agent: Agent[Deps, str] = Agent(
        model,
        system_prompt=system_prompt,
        deps_type=Deps,
        retries=1,
    )

    @agent.tool
    def list_files(ctx: RunContext[Deps], path: str = ".") -> str:
        """List files under a relative path."""
        return ctx.deps.tools.list_files(path)

    @agent.tool
    def read_file(ctx: RunContext[Deps], path: str) -> str:
        """Read a UTF-8 text file."""
        return ctx.deps.tools.read_file(path)

    @agent.tool
    def write_file(ctx: RunContext[Deps], path: str, content: str) -> str:
        """Create or overwrite a file."""
        return ctx.deps.tools.write_file(path, content)

    @agent.tool
    def edit_file(ctx: RunContext[Deps], path: str, old_str: str, new_str: str) -> str:
        """Replace one unique occurrence of old_str with new_str."""
        return ctx.deps.tools.edit_file(path, old_str, new_str)

    @agent.tool
    def run_tests(ctx: RunContext[Deps]) -> str:
        """Run pytest in the workspace."""
        return ctx.deps.tools.run_tests()

    return agent


def _plan_function_model(task_dir: Path) -> FunctionModel:
    """Drive Pydantic AI with the same fake_plan.json used by other harnesses."""
    plan = json_steps(task_dir)
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


def json_steps(task_dir: Path) -> list[dict[str, Any]]:
    import json

    return json.loads((task_dir / "fake_plan.json").read_text(encoding="utf-8"))["steps"]


def run_pydantic_ai(
    *,
    workspace: Path,
    issue_path: Path,
    task_dir: Path,
    task_id: str,
    context_dir: Path | None,
    model_mode: str,
    max_steps: int,
) -> AgentResult:
    if model_mode == "fake":
        # Prefer the shared fake runner for identical CI metrics across harnesses.
        # Also exercise FunctionModel path lightly when HARNESS_PYDANTIC_FUNCTION_MODEL=1.
        import os

        if os.environ.get("HARNESS_PYDANTIC_FUNCTION_MODEL") == "1":
            return _run_with_function_model(
                workspace=workspace,
                issue_path=issue_path,
                task_dir=task_dir,
                task_id=task_id,
                context_dir=context_dir,
                max_steps=max_steps,
            )
        return run_fake_agent(
            harness="pydantic-ai",
            task_id=task_id,
            task_dir=task_dir,
            workspace=workspace,
            max_steps=max_steps,
        )

    model_name = model_id_for_mode(model_mode)
    if model_mode == "openai":
        model = f"openai:{model_name}"
    else:
        model = f"anthropic:{model_name}"

    system = load_system_prompt(context_dir)
    issue = load_issue(issue_path)
    tools = WorkspaceTools(root=workspace)
    agent = build_agent(system, model)
    started = time.perf_counter()
    error: str | None = None
    message = ""
    tokens_in = tokens_out = None
    try:
        result = agent.run_sync(
            f"Issue:\n{issue}\n\nFix the repository. Stop when tests pass.",
            deps=Deps(tools),
            model_settings={"max_tokens": 2048},
        )
        message = str(result.output)
        usage = result.usage()
        tokens_in = getattr(usage, "request_tokens", None) or getattr(usage, "input_tokens", None)
        tokens_out = getattr(usage, "response_tokens", None) or getattr(usage, "output_tokens", None)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    wall_ms = (time.perf_counter() - started) * 1000
    passed = tools.run_tests().startswith("exit_code=0") and error is None
    # run_tests already logged; strip the grading call from fairness? keep it.
    return AgentResult(
        harness="pydantic-ai",
        task_id=task_id,
        passed=passed,
        steps=len(tools.call_log),
        wall_time_ms=round(wall_ms, 2),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=model,
        message=message or ("passed" if passed else "failed"),
        error=error,
        tool_calls=tools.call_log,
    )


def _run_with_function_model(
    *,
    workspace: Path,
    issue_path: Path,
    task_dir: Path,
    task_id: str,
    context_dir: Path | None,
    max_steps: int,
) -> AgentResult:
    system = load_system_prompt(context_dir)
    issue = load_issue(issue_path)
    tools = WorkspaceTools(root=workspace)
    agent = build_agent(system, _plan_function_model(task_dir))
    started = time.perf_counter()
    error: str | None = None
    message = ""
    try:
        result = agent.run_sync(
            f"Issue:\n{issue}\n\nFix the repository. Stop when tests pass.",
            deps=Deps(tools),
        )
        message = str(result.output)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    wall_ms = (time.perf_counter() - started) * 1000
    grade = WorkspaceTools(root=workspace)
    passed = grade.run_tests().startswith("exit_code=0") and error is None
    return AgentResult(
        harness="pydantic-ai",
        task_id=task_id,
        passed=passed,
        steps=min(len(tools.call_log), max_steps),
        wall_time_ms=round(wall_ms, 2),
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        model="fake-function-model",
        message=message or ("passed" if passed else "failed"),
        error=error,
        tool_calls=tools.call_log,
    )
