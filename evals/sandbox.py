from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from evals.discover import Task


@contextmanager
def sandboxed_workspace(task: Task) -> Iterator[Path]:
    """Copy fixture into an isolated temp dir; agent edits never touch canonical tasks."""
    tmp = Path(tempfile.mkdtemp(prefix=f"harness-{task.id}-"))
    try:
        dest = tmp / "workspace"
        shutil.copytree(task.fixture_path, dest)
        yield dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
