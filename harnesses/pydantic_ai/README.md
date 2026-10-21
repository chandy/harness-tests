# Pydantic AI harness

Thin coding agent built with [Pydantic AI](https://ai.pydantic.dev/).

## What you get

- **Typed tools** via `@agent.tool` and `RunContext` deps — args are validated.
- Clean dependency injection (`Deps` holds the sandboxed `WorkspaceTools`).
- First-class **test doubles**: `FunctionModel` / `TestModel` for CI without API keys.

## Tradeoffs

- No built-in durable crash-resume (contrast pi-durable).
- No opinionated planning/subagent tree (contrast Deep Agents).
- You assemble the loop yourself: great for learning, more glue for large systems.

## Run

```bash
# from repo root, after `uv sync`
uv run harness-pydantic-ai \
  --workspace /tmp/ws \
  --issue tasks/01-fix-typo/issue.md \
  --task-dir tasks/01-fix-typo \
  --task-id 01-fix-typo \
  --model fake \
  --json
```

Prefer the top-level evals runner for sandboxed task copies.
