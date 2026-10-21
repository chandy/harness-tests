import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export type ToolCallLog = {
  tool: string;
  args: Record<string, unknown>;
  result_preview: string;
};

export class WorkspaceTools {
  readonly root: string;
  readonly callLog: ToolCallLog[] = [];
  private readonly maxFileBytes = 200_000;

  constructor(root: string) {
    this.root = path.resolve(root);
  }

  private resolve(rel: string): string {
    const target = path.resolve(this.root, rel);
    const relToRoot = path.relative(this.root, target);
    if (relToRoot.startsWith("..") || path.isAbsolute(relToRoot)) {
      throw new Error(`Path escapes workspace: ${rel}`);
    }
    return target;
  }

  private log(tool: string, args: Record<string, unknown>, result: string): string {
    this.callLog.push({ tool, args, result_preview: result.slice(0, 200) });
    return result;
  }

  listFiles(relPath = "."): string {
    const target = this.resolve(relPath);
    if (!fs.existsSync(target)) {
      return this.log("list_files", { path: relPath }, `ERROR: path not found: ${relPath}`);
    }
    if (!fs.statSync(target).isDirectory()) {
      return this.log("list_files", { path: relPath }, `ERROR: not a directory: ${relPath}`);
    }
    const entries: string[] = [];
    const walk = (dir: string) => {
      for (const name of fs.readdirSync(dir).sort()) {
        if (name === "__pycache__" || name === ".pytest_cache" || name === "node_modules") continue;
        const full = path.join(dir, name);
        const st = fs.statSync(full);
        if (st.isDirectory()) walk(full);
        else entries.push(path.relative(this.root, full));
      }
    };
    walk(target);
    return this.log("list_files", { path: relPath }, entries.length ? entries.join("\n") : "(empty)");
  }

  readFile(relPath: string): string {
    const target = this.resolve(relPath);
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      return this.log("read_file", { path: relPath }, `ERROR: file not found: ${relPath}`);
    }
    const data = fs.readFileSync(target);
    if (data.byteLength > this.maxFileBytes) {
      return this.log("read_file", { path: relPath }, `ERROR: file too large (${data.byteLength} bytes)`);
    }
    return this.log("read_file", { path: relPath }, data.toString("utf8"));
  }

  writeFile(relPath: string, content: string): string {
    const target = this.resolve(relPath);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content, "utf8");
    return this.log("write_file", { path: relPath, content: content.slice(0, 80) }, `Wrote ${content.length} bytes to ${relPath}`);
  }

  editFile(relPath: string, oldStr: string, newStr: string): string {
    const target = this.resolve(relPath);
    const args = { path: relPath, old_str: oldStr, new_str: newStr };
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      return this.log("edit_file", args, `ERROR: file not found: ${relPath}`);
    }
    const text = fs.readFileSync(target, "utf8");
    const count = text.split(oldStr).length - 1;
    if (count === 0) return this.log("edit_file", args, "ERROR: old_str not found");
    if (count > 1) return this.log("edit_file", args, `ERROR: old_str found ${count} times; make it unique`);
    fs.writeFileSync(target, text.replace(oldStr, newStr), "utf8");
    return this.log("edit_file", args, `Edited ${relPath}`);
  }

  runTests(): string {
    const python = process.env.HARNESS_PYTHON || "python3";
    const proc = spawnSync(python, ["-m", "pytest", "-q", "--tb=short"], {
      cwd: this.root,
      encoding: "utf8",
      timeout: 60_000,
    });
    const output = `${proc.stdout ?? ""}${proc.stderr ?? ""}`.trim();
    const summary = `exit_code=${proc.status ?? 1}\n${output}`;
    return this.log("run_tests", {}, summary);
  }

  dispatch(name: string, args: Record<string, unknown>): string {
    switch (name) {
      case "list_files":
        return this.listFiles(String(args.path ?? "."));
      case "read_file":
        return this.readFile(String(args.path));
      case "write_file":
        return this.writeFile(String(args.path), String(args.content ?? ""));
      case "edit_file":
        return this.editFile(String(args.path), String(args.old_str ?? ""), String(args.new_str ?? ""));
      case "run_tests":
        return this.runTests();
      default:
        return `ERROR: unknown tool ${name}`;
    }
  }
}
