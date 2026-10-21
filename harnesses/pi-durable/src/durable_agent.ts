import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { Type } from "@earendil-works/pi-ai";
import { createModels } from "@earendil-works/pi-ai/models";
import { openaiProvider } from "@earendil-works/pi-ai/providers/openai";
import { anthropicProvider } from "@earendil-works/pi-ai/providers/anthropic";
import {
  AssistantEntry,
  createRegistry,
  defineExtension,
  defineTool,
  Harness,
  MemoryStorage,
  section,
} from "@earendil-works/pi-durable";
import fs from "node:fs";
import { loadSystemPrompt } from "./context.js";
import { WorkspaceTools } from "./tools.js";
import type { AgentResult } from "./types.js";

export async function runDurableAgent(opts: {
  taskId: string;
  workspace: string;
  issuePath: string;
  contextDir?: string;
  modelMode: "openai" | "anthropic";
  modelId: string;
  maxSteps: number;
}): Promise<AgentResult> {
  const tools = new WorkspaceTools(opts.workspace);
  const systemPrompt = loadSystemPrompt(opts.contextDir);
  const issue = fs.readFileSync(opts.issuePath, "utf8").trim();
  const context = BACKGROUND_CONTEXT;
  const started = performance.now();

  const codingTools = defineExtension({
    name: "coding-agent-tools",
    sections: [
      section("shared-system", () => systemPrompt),
    ],
    tools: [
      defineTool({
        name: "list_files",
        description: "List files under a relative path.",
        parameters: Type.Object({ path: Type.Optional(Type.String()) }),
        execute: async (args) => ({
          output: [{ type: "text" as const, text: tools.listFiles(args.path ?? ".") }],
        }),
      }),
      defineTool({
        name: "read_file",
        description: "Read a UTF-8 text file.",
        parameters: Type.Object({ path: Type.String() }),
        execute: async (args) => ({
          output: [{ type: "text" as const, text: tools.readFile(args.path) }],
        }),
      }),
      defineTool({
        name: "write_file",
        description: "Create or overwrite a file.",
        parameters: Type.Object({ path: Type.String(), content: Type.String() }),
        execute: async (args) => ({
          output: [{ type: "text" as const, text: tools.writeFile(args.path, args.content) }],
        }),
      }),
      defineTool({
        name: "edit_file",
        description: "Replace one unique occurrence of old_str with new_str.",
        parameters: Type.Object({
          path: Type.String(),
          old_str: Type.String(),
          new_str: Type.String(),
        }),
        execute: async (args) => ({
          output: [
            {
              type: "text" as const,
              text: tools.editFile(args.path, args.old_str, args.new_str),
            },
          ],
        }),
      }),
      defineTool({
        name: "run_tests",
        description: "Run pytest in the workspace.",
        parameters: Type.Object({}),
        execute: async () => ({
          output: [{ type: "text" as const, text: tools.runTests() }],
        }),
      }),
    ],
  });

  const models = createModels();
  if (opts.modelMode === "openai") models.setProvider(openaiProvider());
  else models.setProvider(anthropicProvider());

  const registry = createRegistry();
  registry.install(codingTools);

  const harness = await Harness.open(new MemoryStorage(), { models, registry }, context);
  let error: string | undefined;
  let message = "";
  try {
    const root = await harness.root(context, {
      agent: {
        model: {
          provider: opts.modelMode,
          modelId: opts.modelId,
        },
        instructions: `You have at most ~${opts.maxSteps} tool rounds. Stop when tests pass.`,
        cwd: opts.workspace,
      },
    });
    const submission = await root.submit(
      {
        type: "input",
        content: `Issue:\n${issue}\n\nFix the repository using the coding tools. Stop when tests pass.`,
      },
      context,
    );
    const settled = await submission.wait(context);
    if (settled.status === "done" && settled.type === "input") {
      const answer = await root.commit((tx) => tx.entry(AssistantEntry, settled.answer), context);
      const modelParts = answer && "model" in answer ? (answer as { model?: unknown[] }).model : undefined;
      const content = modelParts?.[0];
      message = typeof content === "string" ? content : JSON.stringify(content ?? "");
    } else {
      error = `submission unsettled: ${JSON.stringify(settled)}`;
    }
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  } finally {
    await harness.close(context);
  }

  const grade = new WorkspaceTools(opts.workspace).runTests();
  const passed = grade.startsWith("exit_code=0") && !error;
  return {
    harness: "pi-durable",
    task_id: opts.taskId,
    passed,
    steps: tools.callLog.length,
    wall_time_ms: Math.round((performance.now() - started) * 100) / 100,
    tokens_in: null,
    tokens_out: null,
    cost_usd: null,
    model: `${opts.modelMode}:${opts.modelId}`,
    message: message || (passed ? "passed" : "failed"),
    error: error ?? null,
    tool_calls: tools.callLog,
  };
}
