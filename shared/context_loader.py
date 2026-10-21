from __future__ import annotations

import json
from pathlib import Path

from shared.paths import CONTEXT_DIR, TOOL_CONTRACT_PATH


def load_system_prompt(context_dir: Path | None = None) -> str:
    """Load the shared system prompt plus tool contract for every harness."""
    base = context_dir or CONTEXT_DIR
    prompt = (base / "SYSTEM.md").read_text(encoding="utf-8").strip()
    agents = (base / "AGENTS.md").read_text(encoding="utf-8").strip()
    contract = json.loads(TOOL_CONTRACT_PATH.read_text(encoding="utf-8"))
    tool_lines = ["# Tools", ""]
    for tool in contract["tools"]:
        params = tool.get("parameters") or {}
        param_bits = ", ".join(
            f"{name}: {spec.get('type', 'any')}" for name, spec in params.items()
        )
        tool_lines.append(f"- `{tool['name']}({param_bits})` — {tool['description']}")
    return "\n\n".join([prompt, agents, "\n".join(tool_lines)])


def load_issue(issue_path: Path) -> str:
    return issue_path.read_text(encoding="utf-8").strip()
