# pi-durable harness

Thin coding agent built with [`@earendil-works/pi-durable`](https://earendil.com/posts/pi-durable/).

## What you get

- **Durable crash-resume**: conversations, tool calls, and tasks checkpoint to storage before side effects are trusted.
- Extension model (`defineExtension` / `defineTool`) with typed TypeBox schemas.
- Same tool contract as the Python harnesses (`list_files`, `read_file`, `write_file`, `edit_file`, `run_tests`).
- Path toward **Cloudflare Workers** deployment (see blog post + Earendil docs).

## Tradeoffs

- TypeScript-only stack; Python evals shell out to this package.
- Experimental API — expect churn between releases.
- Real-model path needs `@earendil-works/pi-ai` provider credentials; fake mode uses the shared scripted plan.

## Run

```bash
cd harnesses/pi-durable
pnpm install
pnpm exec tsx src/run.ts \
  --workspace /tmp/ws \
  --issue ../../tasks/01-fix-typo/issue.md \
  --task-dir ../../tasks/01-fix-typo \
  --task-id 01-fix-typo \
  --model fake \
  --json
```

Prefer the top-level evals runner for sandboxed task copies.
