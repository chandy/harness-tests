from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shared.paths import TASKS_DIR


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    path: Path

    @property
    def issue_path(self) -> Path:
        return self.path / "issue.md"

    @property
    def fixture_path(self) -> Path:
        return self.path / "fixture"


def discover_tasks(tasks_dir: Path | None = None) -> list[Task]:
    root = tasks_dir or TASKS_DIR
    tasks: list[Task] = []
    for child in sorted(root.iterdir()):
        meta = child / "task.json"
        if not meta.exists():
            continue
        data = json.loads(meta.read_text(encoding="utf-8"))
        tasks.append(
            Task(
                id=str(data["id"]),
                title=str(data.get("title") or data["id"]),
                path=child,
            )
        )
    return tasks
