from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
CONTEXT_DIR = REPO_ROOT / "context"
TOOL_CONTRACT_PATH = REPO_ROOT / "shared" / "tool_contract.json"
