# Evals

One runner, three harnesses, shared tasks.

```bash
# fake model (default; no API keys)
uv run harness-evals --model fake

# subset
uv run harness-evals --harnesses pydantic-ai,pi-durable --tasks 01-fix-typo,02-off-by-one
```

Each run:

1. Discovers `tasks/*/task.json`
2. Copies `fixture/` into a temp sandbox
3. Invokes the harness CLI with the shared `context/`
4. Grades by re-running pytest in the sandbox
5. Writes `evals/output/results.json` + `results.md`

## Flywheels this enables

1. **Context flywheel** — change `context/SYSTEM.md` / `AGENTS.md` / tool descriptions, re-run evals, keep wins that lift pass rate across harnesses.
2. **Code flywheel** — change harness glue or tool implementations, re-run the same tasks, compare steps/tokens/cost.
