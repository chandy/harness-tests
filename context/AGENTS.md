# Workspace conventions

- Fixtures are tiny Python packages with `src/` and `tests/`.
- Run tests with the `run_tests` tool (pytest). Do not invent another test runner.
- Keep changes minimal: fix the bug described in the issue, nothing else.
- Do not delete tests or weaken assertions.
- File paths given to tools are relative to the workspace root.
