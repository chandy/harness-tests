import fs from "node:fs";
import path from "node:path";
import { WorkspaceTools } from "./tools.js";
import type { AgentResult } from "./types.js";

type PlanStep =
  | { tool: string; args?: Record<string, unknown> }
  | { done: string };

export function runFakeAgent(opts: {
  taskId: string;
  taskDir: string;
  workspace: string;
  maxSteps: number;
}): AgentResult {
  const tools = new WorkspaceTools(opts.workspace);
  const planPath = path.join(opts.taskDir, "fake_plan.json");
  const plan = JSON.parse(fs.readFileSync(planPath, "utf8")).steps as PlanStep[];
  const started = performance.now();
  let steps = 0;
  let message = "";
  let error: string | undefined;

  try {
    for (const step of plan) {
      if (steps >= opts.maxSteps) {
        error = `Exceeded max_steps=${opts.maxSteps}`;
        break;
      }
      steps += 1;
      if ("done" in step) {
        message = String(step.done);
        break;
      }
      tools.dispatch(step.tool, step.args ?? {});
    }
    if (!message && !error) message = "Plan finished without an explicit done step";
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  const grade = new WorkspaceTools(opts.workspace).runTests();
  const passed = grade.startsWith("exit_code=0") && !error;
  return {
    harness: "pi-durable",
    task_id: opts.taskId,
    passed,
    steps,
    wall_time_ms: Math.round((performance.now() - started) * 100) / 100,
    tokens_in: 0,
    tokens_out: 0,
    cost_usd: 0,
    model: "fake",
    message: message || (passed ? "Tests passed" : "Tests failed or agent error"),
    error: error ?? null,
    tool_calls: tools.callLog,
  };
}
