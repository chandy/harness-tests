#!/usr/bin/env node
import { parseArgs } from "node:util";
import { runFakeAgent } from "./fake.js";
import { runDurableAgent } from "./durable_agent.js";
import type { AgentResult } from "./types.js";

function resolveModelMode(requested?: string): "fake" | "openai" | "anthropic" {
  const explicit = (requested || process.env.HARNESS_MODEL || "").trim().toLowerCase();
  if (explicit === "fake" || explicit === "openai" || explicit === "anthropic") return explicit;
  if (process.env.OPENAI_API_KEY) return "openai";
  if (process.env.ANTHROPIC_API_KEY) return "anthropic";
  return "fake";
}

function modelIdFor(mode: "openai" | "anthropic"): string {
  if (mode === "openai") return process.env.HARNESS_OPENAI_MODEL || "gpt-4o-mini";
  return process.env.HARNESS_ANTHROPIC_MODEL || "claude-3-5-haiku-latest";
}

async function main(): Promise<number> {
  const { values } = parseArgs({
    options: {
      workspace: { type: "string" },
      issue: { type: "string" },
      "task-dir": { type: "string" },
      "task-id": { type: "string" },
      "context-dir": { type: "string" },
      model: { type: "string" },
      "max-steps": { type: "string", default: "20" },
      json: { type: "boolean", default: false },
    },
  });

  for (const key of ["workspace", "issue", "task-dir", "task-id"] as const) {
    if (!values[key]) {
      console.error(`Missing --${key}`);
      return 2;
    }
  }

  const mode = resolveModelMode(values.model);
  const maxSteps = Number(values["max-steps"] || 20);
  let result: AgentResult;

  if (mode === "fake") {
    result = runFakeAgent({
      taskId: values["task-id"]!,
      taskDir: values["task-dir"]!,
      workspace: values.workspace!,
      maxSteps,
    });
  } else {
    result = await runDurableAgent({
      taskId: values["task-id"]!,
      workspace: values.workspace!,
      issuePath: values.issue!,
      contextDir: values["context-dir"],
      modelMode: mode,
      modelId: modelIdFor(mode),
      maxSteps,
    });
  }

  if (values.json) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    const status = result.passed ? "PASS" : "FAIL";
    console.log(`[${status}] ${result.harness}/${result.task_id} steps=${result.steps} wall_ms=${result.wall_time_ms}`);
    if (result.message) console.log(result.message);
    if (result.error) console.log(`error: ${result.error}`);
  }
  return result.passed ? 0 : 1;
}

main().then((code) => process.exit(code));
