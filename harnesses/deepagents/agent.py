from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from shared.context_loader import load_issue, load_system_prompt
from shared.fake_agent import run_fake_agent
from shared.model_mode import model_id_for_mode
from shared.results import AgentResult
from shared.tools import WorkspaceTools


def _tool_wrappers(tools: WorkspaceTools) -> list[Any]:
    """Expose the shared tool contract to Deep Agents / LangChain."""

    def list_files(path: str = ".") -> str:
        """List files under a relative path."""
        return tools.list_files(path)

    def read_file(path: str) -> str:
        """Read a UTF-8 text file."""
        return tools.read_file(path)

    def write_file(path: str, content: str) -> str:
        """Create or overwrite a file."""
        return tools.write_file(path, content)

    def edit_file(path: str, old_str: str, new_str: str) -> str:
        """Replace one unique occurrence of old_str with new_str."""
        return tools.edit_file(path, old_str, new_str)

    def run_tests() -> str:
        """Run pytest in the workspace."""
        return tools.run_tests()

    return [list_files, read_file, write_file, edit_file, run_tests]


def _fake_chat_model(task_dir: Path):
    """Minimal LangChain chat model that replays fake_plan.json tool calls."""
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage, BaseMessage, ToolCall
    from langchain_core.outputs import ChatGeneration, ChatResult
    from pydantic import Field, PrivateAttr

    plan = json.loads((task_dir / "fake_plan.json").read_text(encoding="utf-8"))["steps"]

    class PlanChatModel(BaseChatModel):
        model_name: str = Field(default="fake-plan")
        _idx: int = PrivateAttr(default=0)
        _plan: list[dict[str, Any]] = PrivateAttr(default_factory=list)

        def __init__(self, steps: list[dict[str, Any]], **kwargs: Any):
            super().__init__(**kwargs)
            self._plan = steps
            self._idx = 0

        @property
        def _llm_type(self) -> str:
            return "fake-plan"

        def _generate(
            self,
            messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: Any = None,
            **kwargs: Any,
        ) -> ChatResult:
            del messages, stop, run_manager, kwargs
            if self._idx >= len(self._plan):
                msg = AIMessage(content="Done.")
                return ChatResult(generations=[ChatGeneration(message=msg)])
            step = self._plan[self._idx]
            self._idx += 1
            if "done" in step:
                msg = AIMessage(content=str(step["done"]))
                return ChatResult(generations=[ChatGeneration(message=msg)])
            tool_call = ToolCall(
                name=step["tool"],
                args=dict(step.get("args") or {}),
                id=f"call_{self._idx}",
            )
            msg = AIMessage(content="", tool_calls=[tool_call])
            return ChatResult(generations=[ChatGeneration(message=msg)])

        def bind_tools(self, tools: Any, **kwargs: Any) -> PlanChatModel:
            del tools, kwargs
            return self

    return PlanChatModel(plan)


def run_deepagents(
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
        # Shared fake runner keeps CI metrics identical across harnesses.
        # Set HARNESS_DEEPAGENTS_NATIVE_FAKE=1 to exercise create_deep_agent + PlanChatModel.
        import os

        if os.environ.get("HARNESS_DEEPAGENTS_NATIVE_FAKE") == "1":
            return _run_native(
                workspace=workspace,
                issue_path=issue_path,
                task_dir=task_dir,
                task_id=task_id,
                context_dir=context_dir,
                model=_fake_chat_model(task_dir),
                model_label="fake-plan-chat",
                max_steps=max_steps,
            )
        return run_fake_agent(
            harness="deepagents",
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
    return _run_native(
        workspace=workspace,
        issue_path=issue_path,
        task_dir=task_dir,
        task_id=task_id,
        context_dir=context_dir,
        model=model,
        model_label=model,
        max_steps=max_steps,
    )


def _run_native(
    *,
    workspace: Path,
    issue_path: Path,
    task_dir: Path,
    task_id: str,
    context_dir: Path | None,
    model: Any,
    model_label: str,
    max_steps: int,
) -> AgentResult:
    from deepagents import create_deep_agent

    system = load_system_prompt(context_dir)
    issue = load_issue(issue_path)
    tools = WorkspaceTools(root=workspace)
    agent = create_deep_agent(
        model=model,
        tools=_tool_wrappers(tools),
        system_prompt=system,
    )
    started = time.perf_counter()
    error: str | None = None
    message = ""
    try:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Issue:\n{issue}\n\n"
                            "Use list_files/read_file/edit_file/write_file/run_tests. "
                            "Stop when tests pass."
                        ),
                    }
                ]
            },
            config={"recursion_limit": max(max_steps * 4, 40)},
        )
        msgs = result.get("messages") or []
        if msgs:
            last = msgs[-1]
            message = getattr(last, "content", None) or str(last)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    wall_ms = (time.perf_counter() - started) * 1000
    grade = WorkspaceTools(root=workspace).run_tests()
    passed = grade.startswith("exit_code=0") and error is None
    return AgentResult(
        harness="deepagents",
        task_id=task_id,
        passed=passed,
        steps=len(tools.call_log),
        wall_time_ms=round(wall_ms, 2),
        model=model_label,
        message=str(message)[:500] if message else ("passed" if passed else "failed"),
        error=error,
        tool_calls=tools.call_log,
    )
