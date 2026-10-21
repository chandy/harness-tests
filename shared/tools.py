from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WorkspaceTools:
    """Sandbox filesystem + test runner used by Python harnesses."""

    root: Path
    max_file_bytes: int = 200_000
    call_log: list[dict[str, Any]] = field(default_factory=list)

    def _resolve(self, rel: str) -> Path:
        root = self.root.resolve()
        target = (root / rel).resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"Path escapes workspace: {rel}")
        return target

    def _log(self, name: str, args: dict[str, Any], result: str) -> str:
        self.call_log.append({"tool": name, "args": args, "result_preview": result[:200]})
        return result

    def list_files(self, path: str = ".") -> str:
        target = self._resolve(path)
        if not target.exists():
            return self._log("list_files", {"path": path}, f"ERROR: path not found: {path}")
        if not target.is_dir():
            return self._log("list_files", {"path": path}, f"ERROR: not a directory: {path}")
        entries: list[str] = []
        for child in sorted(target.rglob("*")):
            if child.is_file() and "__pycache__" not in child.parts and ".pytest_cache" not in child.parts:
                entries.append(str(child.relative_to(self.root)))
        text = "\n".join(entries) if entries else "(empty)"
        return self._log("list_files", {"path": path}, text)

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.exists() or not target.is_file():
            return self._log("read_file", {"path": path}, f"ERROR: file not found: {path}")
        data = target.read_bytes()
        if len(data) > self.max_file_bytes:
            return self._log("read_file", {"path": path}, f"ERROR: file too large ({len(data)} bytes)")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return self._log("read_file", {"path": path}, "ERROR: not a UTF-8 text file")
        return self._log("read_file", {"path": path}, text)

    def write_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        msg = f"Wrote {len(content)} bytes to {path}"
        return self._log("write_file", {"path": path, "content": content[:80]}, msg)

    def edit_file(self, path: str, old_str: str, new_str: str) -> str:
        target = self._resolve(path)
        if not target.exists() or not target.is_file():
            return self._log(
                "edit_file",
                {"path": path, "old_str": old_str, "new_str": new_str},
                f"ERROR: file not found: {path}",
            )
        text = target.read_text(encoding="utf-8")
        count = text.count(old_str)
        if count == 0:
            return self._log(
                "edit_file",
                {"path": path, "old_str": old_str, "new_str": new_str},
                "ERROR: old_str not found",
            )
        if count > 1:
            return self._log(
                "edit_file",
                {"path": path, "old_str": old_str, "new_str": new_str},
                f"ERROR: old_str found {count} times; make it unique",
            )
        target.write_text(text.replace(old_str, new_str, 1), encoding="utf-8")
        return self._log(
            "edit_file",
            {"path": path, "old_str": old_str, "new_str": new_str},
            f"Edited {path}",
        )

    def run_tests(self) -> str:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=short"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        summary = f"exit_code={proc.returncode}\n{output.strip()}"
        return self._log("run_tests", {}, summary)

    def dispatch(self, name: str, args: dict[str, Any]) -> str:
        if name == "list_files":
            return self.list_files(**args)
        if name == "read_file":
            return self.read_file(**args)
        if name == "write_file":
            return self.write_file(**args)
        if name == "edit_file":
            return self.edit_file(**args)
        if name == "run_tests":
            return self.run_tests()
        return f"ERROR: unknown tool {name}"
