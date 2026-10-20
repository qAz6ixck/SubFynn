#!/usr/bin/env node
// SubFynn E2E Test Suite Runner (Node.js ESM wrapper)
// Strictly ZERO emojis permitted in inputs, assertions, console output, and reports.

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, "..");
const pythonRunner = join(__dirname, "runner.py");

const pythonExec = process.platform === "win32" ? "python" : "python3";
const args = [pythonRunner, ...process.argv.slice(2)];

const child = spawn(pythonExec, args, {
  cwd: projectRoot,
  stdio: "inherit",
  shell: false
});

child.on("close", (code) => {
  process.exit(code ?? 1);
});

child.on("error", (err) => {
  console.error("[ERROR] Failed to spawn python runner:", err.message);
  process.exit(1);
});
