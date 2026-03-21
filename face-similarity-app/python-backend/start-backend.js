#!/usr/bin/env node
/**
 * Cross-platform backend launcher.
 *
 * Resolution order:
 *   1. .venv/bin/python      (Linux / macOS venv)
 *   2. .venv/Scripts/python  (Windows venv)
 *   3. python3.11            (system — Linux/Mac)
 *   4. python3               (system — Linux/Mac)
 *   5. python                (system — Windows / fallback)
 *
 * Also sets TF_ENABLE_ONEDNN_OPTS=0 to prevent TensorFlow oneDNN
 * instability / segfaults on EC2 and other Linux environments.
 */
const { spawnSync, spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const isWin = process.platform === "win32";

const candidates = [
  isWin
    ? path.join(".venv", "Scripts", "python.exe")
    : path.join(".venv", "bin", "python"),
  "python3.11",
  "python3",
  "python",
];

function exists(bin) {
  if (bin.startsWith(".")) {
    return fs.existsSync(bin);
  }
  const result = spawnSync(bin, ["--version"], { stdio: "ignore" });
  return result.status === 0;
}

const python = candidates.find(exists);

if (!python) {
  console.error(
    "ERROR: No Python executable found. Install Python 3.11 and try again."
  );
  process.exit(1);
}

console.log(`[backend] Using Python: ${python}`);

const env = {
  ...process.env,
  // Disable oneDNN custom ops — prevents segfaults on Linux/EC2 with TF 2.13
  TF_ENABLE_ONEDNN_OPTS: "0",
  // Suppress TF informational logs (0=all, 1=info, 2=warn, 3=error)
  TF_CPP_MIN_LOG_LEVEL: "2",
};

const proc = spawn(python, ["app_v2.py"], { stdio: "inherit", env });
proc.on("exit", (code) => process.exit(code ?? 0));
