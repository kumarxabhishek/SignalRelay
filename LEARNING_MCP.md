# MCP, without the buzzwords

## The short version

An **MCP server** is a small program that gives an AI host (such as Claude
Desktop) a menu of tools it can call. Think of it as a standard plug socket:
the host does not need to know how market data is fetched; it only sees tool
names, arguments, and structured results.

This project has two roles at once:

```text
Claude Desktop --calls--> SignalRelay --calls--> NSE-MCP --fetches--> NSE/Yahoo
                         (our server)                 (existing server)
```

We are not copying NSE-MCP. It owns low-level data fetching and its NSE cookie
handling. We own the higher-level layer: converting several raw sources into
typed evidence now, then auditable multi-signal explanations in later phases.

## What happens when you ask for RELIANCE

1. Claude Desktop starts `server.app` and discovers our two tools over stdio.
2. It calls one of them with `{ "symbol": "RELIANCE" }`.
3. Our async handler asks the typed data layer for quote, deals, insider trades,
   FII/DII flows, and delivery history.
4. The data layer starts NSE-MCP as a separate subprocess with its **own**
   input/output pipes. It never shares the pipe used by Claude Desktop.
5. NSE-MCP gets public market data and returns JSON. We normalize dates and
   numbers into Python dataclasses, then return source-tagged JSON to Claude.

Phase 1 stops there. Later, ordinary Python rules can decide whether a pattern
exists. Only then should an LLM write an explanation from a restricted evidence
object, followed by a verification pass.

## Why the engineering details matter

- **stdio is a protocol channel:** a stray `print()` on server stdout can make
  JSON-RPC unreadable. Server logging goes to stderr instead.
- **async prevents one request blocking another:** blocking work must be moved
  off the event loop; the Phase 1 MCP calls are already async.
- **typed records prevent quiet errors:** `10-Jul-2026` becomes a `date`, not a
  string that later comparison code may mishandle.
- **one symbol normalizer prevents provider mix-ups:** NSE-MCP uses `RELIANCE`,
  Yahoo/yfinance uses `RELIANCE.NS`, and Nifty 50 is `^NSEI`.
- **the TTL cache protects the upstream:** repeated requests reuse a recent
  result rather than needlessly hitting the data provider.

## What you should read next

Read the official [MCP architecture introduction](https://modelcontextprotocol.io/docs/learn/architecture)
and then inspect `server/app.py` followed by `data_layer/client.py`. That is the
entire Phase 1 request path.
