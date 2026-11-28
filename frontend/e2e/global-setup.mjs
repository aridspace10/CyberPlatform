import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const backendScript = resolve(frontend, "e2e/backend_server.py");
const viteScript = resolve(frontend, "node_modules/vite/bin/vite.js");

async function stopProcess(child) {
  if (!child) return;
  if (child.exitCode !== null || child.signalCode !== null) return;
  child.kill("SIGTERM");
  await new Promise((resolveExit, rejectExit) => {
    const timeout = setTimeout(() => rejectExit(new Error("E2E server did not stop")), 10000);
    child.once("close", () => { clearTimeout(timeout); resolveExit(); });
  });
}

async function waitFor(url, child, diagnostics) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`E2E server exited: ${diagnostics()}`);
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch { /* wait for startup */ }
    await new Promise(resolveWait => setTimeout(resolveWait, 250));
  }
  throw new Error(`E2E server did not start: ${diagnostics()}`);
}

export default async function globalSetup() {
  const dataDir = await mkdtemp(join(tmpdir(), "cyberplatform-e2e-"));
  const python = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  const child = spawn(python, [backendScript], {
    cwd: dataDir,
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  let diagnostics = "";
  child.stdout.on("data", chunk => { diagnostics += chunk.toString(); });
  child.stderr.on("data", chunk => { diagnostics += chunk.toString(); });
  let vite;
  let viteDiagnostics = "";

  const stop = async () => {
    await stopProcess(vite);
    await stopProcess(child);
    await rm(dataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  };

  try {
    await waitFor("http://127.0.0.1:8765/", child, () => diagnostics);
    vite = spawn(process.execPath, [viteScript, "--host", "127.0.0.1", "--port", "5174", "--strictPort"], {
      cwd: frontend,
      env: { ...process.env, VITE_BACKEND_URL: "http://127.0.0.1:8765" },
      stdio: ["ignore", "pipe", "pipe"],
    });
    vite.stdout.on("data", chunk => { viteDiagnostics += chunk.toString(); });
    vite.stderr.on("data", chunk => { viteDiagnostics += chunk.toString(); });
    await waitFor("http://127.0.0.1:5174/", vite, () => viteDiagnostics);
    return stop;
  } catch (error) {
    await stop();
    throw error;
  }
}
