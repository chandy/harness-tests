# Benchmark tasks

Each task is a tiny coding problem:

| Path | Contents |
|------|----------|
| `issue.md` | Task description given to the agent |
| `fixture/` | Sandboxed repo the agent may edit |
| `fake_plan.json` | Scripted tool calls for fake-model / CI mode |
| `task.json` | Stable task id + metadata |

Hidden grading = re-running the fixture tests after the agent finishes (copied into a temp workspace so agents never mutate the canonical fixtures).

To add a task: copy an existing folder, break a small function, write tests that fail on the broken code, and author a `fake_plan.json` that repairs it with the shared tools.
