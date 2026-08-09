/**
 * Phase 0 probe. This is a standalone client, never part of the server's
 * stdio stream. Its stdout is intentionally the JSON discovery result.
 */
// Phase 0 runs before SignalRelay has its own dependency environment.
// Use the pinned NSE-MCP SDK installation being probed.
import { Client } from "../.vendor/NSE-MCP/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js";
import { StdioClientTransport } from "../.vendor/NSE-MCP/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js";

const node = process.env.NODE_BINARY;
const serverEntry = process.env.NSE_MCP_ENTRY;

if (!node || !serverEntry) {
  throw new Error("NODE_BINARY and NSE_MCP_ENTRY must be set");
}

const client = new Client(
  { name: "signalrelay-phase-zero", version: "0.1.0" },
  { capabilities: {} },
);
const transport = new StdioClientTransport({ command: node, args: [serverEntry] });

try {
  await client.connect(transport);
  const listed = await client.listTools();
  const liveCalls = {};

  for (const [name, args] of [
    ["get_quote", { symbol: "RELIANCE" }],
    ["get_bulk_deals", { symbol: "RELIANCE" }],
    ["get_insider_trading", { symbol: "RELIANCE" }],
    ["get_fii_dii_activity", { limit: 2 }],
    ["get_nifty_indices", { name: "NIFTY 50" }],
  ]) {
    try {
      liveCalls[name] = await client.callTool({ name, arguments: args });
    } catch (error) {
      liveCalls[name] = { transportError: error instanceof Error ? error.message : String(error) };
    }
  }

  process.stdout.write(`${JSON.stringify({ tools: listed.tools, liveCalls }, null, 2)}\n`);
} finally {
  await transport.close();
}
