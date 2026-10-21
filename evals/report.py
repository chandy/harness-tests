from __future__ import annotations

import json
from pathlib import Path

from shared.results import AgentResult


def write_reports(results: list[AgentResult], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "results.json"
    md_path = out_dir / "results.md"
    payload = [r.to_dict() for r in results]
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(results), encoding="utf-8")
    return json_path, md_path


def render_markdown(results: list[AgentResult]) -> str:
    lines = [
        "# Eval results",
        "",
        "| Harness | Task | Pass | Steps | Tokens in/out | Wall ms | Cost USD | Model |",
        "|---|---|---|---:|---|---:|---:|---|",
    ]
    for r in results:
        tokens = "—/—"
        if r.tokens_in is not None or r.tokens_out is not None:
            tokens = f"{r.tokens_in if r.tokens_in is not None else '—'}/{r.tokens_out if r.tokens_out is not None else '—'}"
        cost = "—" if r.cost_usd is None else f"{r.cost_usd:.4f}"
        lines.append(
            f"| {r.harness} | {r.task_id} | {'✅' if r.passed else '❌'} | {r.steps} | {tokens} | {r.wall_time_ms:.1f} | {cost} | {r.model} |"
        )

    passed = sum(1 for r in results if r.passed)
    lines.extend(
        [
            "",
            f"**Summary:** {passed}/{len(results)} passed",
            "",
        ]
    )

    # Per-harness rollup
    harnesses = sorted({r.harness for r in results})
    lines.extend(["## By harness", ""])
    for h in harnesses:
        subset = [r for r in results if r.harness == h]
        ok = sum(1 for r in subset if r.passed)
        avg_steps = sum(r.steps for r in subset) / max(len(subset), 1)
        avg_ms = sum(r.wall_time_ms for r in subset) / max(len(subset), 1)
        lines.append(f"- **{h}**: {ok}/{len(subset)} pass · avg steps {avg_steps:.1f} · avg wall {avg_ms:.1f} ms")
    lines.append("")
    return "\n".join(lines)
