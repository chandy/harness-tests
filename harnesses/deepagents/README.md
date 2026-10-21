# LangChain Deep Agents harness

Thin coding agent built with [`deepagents`](https://github.com/langchain-ai/deepagents) (`create_deep_agent`).

## What you get

- **Planning + subagents** baked into the harness (`task` tool, filesystem middleware).
- Context management helpers (skills/memory options as the library evolves).
- LangChain model ecosystem (`openai:...`, `anthropic:...`, or a custom chat model).

## Tradeoffs

- Heavier default tool surface (built-ins merge with ours) — keep prompts explicit about which tools to use for fair comparisons.
- Python-only; not a durable crash-resume runtime by itself.
- API is still moving quickly; pin versions in `pyproject.toml`.

## Run

```bash
uv run harness-deepagents \
  --workspace /tmp/ws \
  --issue tasks/01-fix-typo/issue.md \
  --task-dir tasks/01-fix-typo \
  --task-id 01-fix-typo \
  --model fake \
  --json
```

Fake mode defaults to the shared scripted runner. Set `HARNESS_DEEPAGENTS_NATIVE_FAKE=1` to drive `create_deep_agent` with a plan-replaying chat model.
