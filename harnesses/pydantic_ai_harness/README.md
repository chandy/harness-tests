# Pydantic AI Harness

Thin coding agent built with [`pydantic-ai-harness`](https://pydantic.dev/docs/ai/harness/) — specifically **`Coder` + `LocalWorkspace`**, not hand-rolled `@agent.tool` wrappers.

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import LocalWorkspace
from pydantic_ai_harness.coder import Coder

agent = Agent(
    model,
    capabilities=[
        LocalWorkspace(<sandbox dir>),
        Coder(instructions=<shared context/>),
    ],
)
```

## What you get

- **Capabilities** — composeable units (`Coder`, sandboxes, memory, compaction, …) on any `Agent`
- **Coder** — built-in coding tools + default autonomous instructions + JSON arg repair + context controls
- **Workspaces / sandboxes** — `LocalWorkspace` locally; swap for Modal / E2B / Daytona / etc. without rewriting tools
- **Durable execution** — Pydantic AI’s durable-exec story (DBOS / Temporal / …) can wrap the same agent loop
- **Typed agent loop** — still plain Pydantic AI underneath (`FunctionModel` / `TestModel` for CI)

## Tool mapping (shared contract → Coder)

| Shared contract (`shared/tool_contract.json`) | Coder / FileSystem / Shell |
|---|---|
| `list_files(path)` | `list_files(path, glob?)` |
| `read_file(path)` | `read_file(path, offset?, limit?)` |
| `write_file(path, content)` | `write_file(path, content)` |
| `edit_file(path, old_str, new_str)` | `edit_file(path, old_text, new_text)` — **arg names differ** |
| `run_tests()` | `shell(command=…pytest…)` — **no dedicated test tool** |
| *(none)* | `grep(pattern, path?, …)` |
| *(none)* | `delegate_task(...)` — sub-agent handoff |

Fake-mode `fake_plan.json` files stay in the shared contract vocabulary; this harness translates `run_tests` → `shell` and `old_str`/`new_str` → `old_text`/`new_text` before replaying through **`FunctionModel` on the real Coder loop**.

## Tradeoffs

- Shell is unrestricted inside the workspace (powerful; needs trust or a remote sandbox).
- Extra tools (`grep`, `delegate_task`) mean live models see a wider surface than Deep Agents / pi-durable in this repo.
- Python-only; durable crash-resume is a separate capability stack vs pi-durable’s built-in storage model.

## Run

```bash
uv run harness-pydantic-ai-harness \
  --workspace /tmp/ws \
  --issue tasks/01-fix-typo/issue.md \
  --task-dir tasks/01-fix-typo \
  --task-id 01-fix-typo \
  --model fake \
  --json
```

Prefer the top-level evals runner for sandboxed task copies.
