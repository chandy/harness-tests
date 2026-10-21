from __future__ import annotations

import argparse
from pathlib import Path

from evals.discover import discover_tasks
from evals.harness_runners import HARNESSES, run_harness
from evals.report import render_markdown, write_reports
from evals.sandbox import sandboxed_workspace
from shared.model_mode import resolve_model_mode
from shared.paths import REPO_ROOT
from shared.results import AgentResult


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run coding-agent evals across harnesses")
    parser.add_argument(
        "--harnesses",
        default=",".join(HARNESSES),
        help=f"Comma-separated harnesses: {', '.join(HARNESSES)}",
    )
    parser.add_argument("--tasks", default=None, help="Comma-separated task ids (default: all)")
    parser.add_argument("--model", default=None, help="fake | openai | anthropic")
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "evals" / "output",
        help="Directory for results.json / results.md",
    )
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args(argv)

    model = resolve_model_mode(args.model)
    harnesses = [h.strip() for h in args.harnesses.split(",") if h.strip()]
    for h in harnesses:
        if h not in HARNESSES:
            raise SystemExit(f"Unknown harness {h!r}; choose from {HARNESSES}")

    tasks = discover_tasks()
    if args.tasks:
        wanted = {t.strip() for t in args.tasks.split(",") if t.strip()}
        tasks = [t for t in tasks if t.id in wanted]
        missing = wanted - {t.id for t in tasks}
        if missing:
            raise SystemExit(f"Unknown tasks: {sorted(missing)}")

    results: list[AgentResult] = []
    for harness in harnesses:
        for task in tasks:
            print(f"→ {harness} / {task.id} (model={model})")
            with sandboxed_workspace(task) as workspace:
                result = run_harness(
                    harness,
                    task,
                    workspace,
                    model=model,
                    max_steps=args.max_steps,
                )
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] steps={result.steps} wall_ms={result.wall_time_ms}")
            if result.error:
                print(f"  error: {result.error}")
            if args.fail_fast and not result.passed:
                break
        if args.fail_fast and results and not results[-1].passed:
            break

    json_path, md_path = write_reports(results, args.out)
    print()
    print(render_markdown(results))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
