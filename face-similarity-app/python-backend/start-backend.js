#!/usr/bin/env node
/**
 * Cross-platform backend launcher.
 * Tries venv Python first, falls back to system python3.11 / python.
 */
const { spawnSync, spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

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
  // For relative paths, check file existence; for system commands, probe with --version
  if (bin.startsWith(".")) {
    return fs.existsSync(bin);
  }
  const result = spawnSync(bin, ["--version"], { stdio: "ignore" });
  return result.status === 0;
}

const python = candidates.find(exists);

if (!python) {
  console.error("ERROR: No Python executable found. Install Python 3.11 and try again.");
  process.exit(1);
}

console.log(`Using Python: ${python}`);

const proc = spawn(python, ["app_v2.py"], { stdio: "inherit" });
proc.on("exit", (code) => process.exit(code ?? 0));
