from __future__ import annotations

from shared.paths import CONTEXT_DIR

from harnesses.cli_common import build_parser, emit_result, resolved_mode
from harnesses.pydantic_ai.agent import run_pydantic_ai


def main(argv: list[str] | None = None) -> int:
    parser = build_parser("pydantic-ai")
    args = parser.parse_args(argv)
    mode = resolved_mode(args)
    result = run_pydantic_ai(
        workspace=args.workspace.resolve(),
        issue_path=args.issue.resolve(),
        task_dir=args.task_dir.resolve(),
        task_id=args.task_id,
        context_dir=(args.context_dir or CONTEXT_DIR).resolve(),
        model_mode=mode,
        max_steps=args.max_steps,
    )
    return emit_result(result, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
