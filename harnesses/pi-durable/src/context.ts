import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(here, "../../..");

export function loadSystemPrompt(contextDir?: string): string {
  const base = contextDir ?? path.join(REPO_ROOT, "context");
  const prompt = fs.readFileSync(path.join(base, "SYSTEM.md"), "utf8").trim();
  const agents = fs.readFileSync(path.join(base, "AGENTS.md"), "utf8").trim();
  const contract = JSON.parse(
    fs.readFileSync(path.join(REPO_ROOT, "shared/tool_contract.json"), "utf8"),
  ) as {
    tools: Array<{ name: string; description: string; parameters?: Record<string, { type?: string }> }>;
  };
  const toolLines = ["# Tools", ""];
  for (const tool of contract.tools) {
    const params = tool.parameters ?? {};
    const paramBits = Object.entries(params)
      .map(([name, spec]) => `${name}: ${spec.type ?? "any"}`)
      .join(", ");
    toolLines.push(`- \`${tool.name}(${paramBits})\` — ${tool.description}`);
  }
  return [prompt, agents, toolLines.join("\n")].join("\n\n");
}
