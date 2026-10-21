from __future__ import annotations

import argparse
import json
from pathlib import Path

from shared.model_mode import resolve_model_mode
from shared.results import AgentResult


def build_parser(harness_name: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=f"Run the {harness_name} coding agent")
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--issue", type=Path, required=True)
    p.add_argument("--task-dir", type=Path, required=True)
    p.add_argument("--task-id", required=True)
    p.add_argument("--context-dir", type=Path, default=None)
    p.add_argument("--model", default=None, help="fake | openai | anthropic")
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument("--json", action="store_true", help="Print AgentResult JSON to stdout")
    return p


def emit_result(result: AgentResult, as_json: bool) -> int:
    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.harness}/{result.task_id} steps={result.steps} wall_ms={result.wall_time_ms}")
        if result.message:
            print(result.message)
        if result.error:
            print(f"error: {result.error}")
    return 0 if result.passed else 1


def resolved_mode(args: argparse.Namespace) -> str:
    return resolve_model_mode(args.model)
