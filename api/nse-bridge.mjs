import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const timeoutMs = Number(process.env.NSE_MCP_TIMEOUT_SECONDS ?? 20) * 1000;
const root = process.cwd();
const wrapper = path.join(root, "scripts", "nse_mcp_stdio_wrapper.mjs");
const entrypoint = process.env.SIGNALRELAY_NSE_MCP_ENTRY
  ?? path.join(root, ".vendor", "NSE-MCP", "dist", "index.js");

function send(res, status, payload) {
  res.status(status).setHeader("Content-Type", "application/json").send(JSON.stringify(payload));
}

function callTool(name, arguments_) {
  return new Promise((resolve, reject) => {
    if (!existsSync(entrypoint)) {
      reject(new Error("NSE-MCP entrypoint is not bundled in this deployment"));
      return;
    }
    const child = spawn(process.execPath, [wrapper, entrypoint], { stdio: ["pipe", "pipe", "pipe"] });
    let buffer = "";
    let stderr = "";
    let initialized = false;
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error("NSE-MCP bridge timed out"));
    }, timeoutMs);
    const fail = (error) => {
      clearTimeout(timer);
      reject(error);
    };
    child.once("error", fail);
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.stdout.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        let message;
        try { message = JSON.parse(line); } catch { continue; }
        if (message.id === 1 && !initialized) {
          initialized = true;
          child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
          child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name, arguments: arguments_ } }) + "\n");
        } else if (message.id === 2) {
          clearTimeout(timer);
          child.kill();
          if (message.error) fail(new Error(message.error.message ?? "NSE-MCP tool failed"));
          else resolve(message.result);
        }
      }
    });
    child.once("close", (code) => {
      if (!initialized && code !== 0) fail(new Error(stderr || `NSE-MCP exited with code ${code}`));
    });
    child.stdin.write(JSON.stringify({
      jsonrpc: "2.0", id: 1, method: "initialize",
      params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "SignalRelay Vercel bridge", version: "0.1.0" } },
    }) + "\n");
  });
}

export default async function handler(req, res) {
  if (req.method !== "POST") return send(res, 405, { detail: "Method not allowed" });
  const expected = process.env.SIGNALRELAY_NSE_BRIDGE_TOKEN;
  if (!expected || req.headers["x-signalrelay-bridge-token"] !== expected) return send(res, 401, { detail: "Unauthorized" });
  const { name, arguments: arguments_ } = typeof req.body === "string" ? JSON.parse(req.body) : req.body ?? {};
  if (typeof name !== "string" || !arguments_ || typeof arguments_ !== "object") return send(res, 422, { detail: "Tool name and arguments are required" });
  try {
    return send(res, 200, { result: await callTool(name, arguments_) });
  } catch (error) {
    console.error(JSON.stringify({ event: "nse_bridge_failed", error: String(error) }));
    return send(res, 502, { detail: "NSE market-data bridge is unavailable" });
  }
}
