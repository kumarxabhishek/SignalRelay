/**
 * Keep upstream library diagnostics out of the JSON-RPC stdout channel.
 * NSE-MCP writes protocol frames directly; only console diagnostics are moved.
 */
import { pathToFileURL } from "node:url";

for (const method of ["log", "info", "warn", "error"]) {
  console[method] = (...items) => {
    process.stderr.write(`${items.map(String).join(" ")}\n`);
  };
}

const entrypoint = process.argv[2];
if (!entrypoint) {
  throw new Error("NSE-MCP entrypoint argument is required");
}
await import(pathToFileURL(entrypoint).href);
