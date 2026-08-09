# SignalRelay

`SignalRelay` is a Python MCP server and HTTP API for grounded,
source-traceable NSE market research. It combines typed NSE-MCP data with
deterministic signal rules, corporate-event context, and an optional
evidence-constrained explanation flow. It does **not** predict prices or make
investment recommendations.

NSE-MCP by [manitgupta](https://github.com/manitgupta/NSE-MCP) is the pinned
underlying data server. This project is an MCP *client* to it and an MCP
*server* to Claude Desktop or another host. Phase 3 adds an optional,
evidence-constrained Claude explanation and verification pipeline. A
conditional quality gate withholds an explanation when our pipeline cannot
fully trace or validate the required NSE-MCP evidence; it never predicts prices.
Transient evidence failures receive one fresh-data retry before the explanation
is withheld.

## Run locally

1. Create the pinned dependency: `powershell -ExecutionPolicy Bypass -File scripts/setup_nse_mcp.ps1`.
2. Create a virtual environment and install: `.venv\\Scripts\\python.exe -m pip install -e ".[dev]"`.
3. Configure an MCP host with the config below, then restart the host.

```json
{
  "mcpServers": {
    "SignalRelay": {
      "command": "C:\\absolute\\path\\to\\SignalRelay\\.venv\\Scripts\\python.exe",
      "args": ["-m", "server.app"],
      "env": {
        "NODE_BINARY": "C:\\path\\to\\node.exe",
        "NSE_MCP_ENTRY": "C:\\absolute\\path\\to\\SignalRelay\\.vendor\\NSE-MCP\\dist\\index.js",
        "ANTHROPIC_API_KEY": "optional: required only for get_signalrelay_explained_report"
      }
    }
  }
}
```

The available public tools are `get_signalrelay_signal(symbol)` and
`get_signalrelay_explained_report(symbol)`. The first returns deterministic flags,
material-event context, limitations, and raw source-tagged inputs. The second
uses Claude only when `ANTHROPIC_API_KEY` is configured; otherwise it returns a
clear no-key error instead of inventing an explanation.

## Run the dashboard API

```powershell
.venv\Scripts\python.exe -m uvicorn api.app:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` for the generated API documentation. The
API returns `422` for invalid ticker format, `404` for an unknown but
well-formed NSE symbol, and `503` when required market data is temporarily
unavailable. It never presents an unknown ticker as a no-signal result.

## Deploy the HTTP API on Vercel

SignalRelay supports both deployment modes from this repository. MCP clients
continue to start `python -m server.app` over stdio. Vercel invokes
`api/index.py` for HTTP requests and a private Node bridge at
`/api/nse-bridge` for the pinned NSE-MCP dependency; the MCP stdio entrypoint
is unchanged.

Import the repository into Vercel. `vercel.json` builds the pinned NSE-MCP
dependency and routes `/health`, `/ready`, and `/v1/*` to FastAPI. Set these
production environment variables:

```text
SIGNALRELAY_ALLOWED_ORIGINS=https://signal-relay-watch.lovable.app
SIGNALRELAY_API_TOKEN=<long random secret>
SIGNALRELAY_NSE_BRIDGE_URL=https://<your-vercel-domain>/api/nse-bridge
SIGNALRELAY_NSE_BRIDGE_TOKEN=<different long random secret>
NSE_MCP_TIMEOUT_SECONDS=20
```

Set `ANTHROPIC_API_KEY` and `SIGNALRELAY_CLAUDE_MODEL` only if verified
explanations are enabled. Do not expose either token in Lovable/browser code:
call `/v1/reports` through a server-side Lovable/Supabase Edge Function that
adds `X-API-Key`. Verify `GET /ready` before setting
`VITE_SIGNALRELAY_API_URL` in the Lovable project.

Run all automated checks with:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Read [LEARNING_MCP.md](LEARNING_MCP.md) before running it; it explains the
architecture in plain language. Phase 0 findings are in [data_gaps.md](data_gaps.md)
and Phase 2’s exact rule contracts are in [PHASE_2_RULES.md](PHASE_2_RULES.md).
Phase 3 guardrails are in [PHASE_3_GUARDRAILS.md](PHASE_3_GUARDRAILS.md).
The Lovable/dashboard HTTP contract is in [DASHBOARD_API.md](DASHBOARD_API.md).
Operational environment and deployment guidance is in [OPERATIONS.md](OPERATIONS.md).
The dashboard should expose the response's `source_status` beside every report,
so users can see data availability and the NIFTY source date. Delivery-spike
detection is currently disabled until a verified delivery-percentage-history
source is added; it is not represented as a no-signal result.

## Limits

This is research software, not investment advice. It does not forecast price
movement. Historical delivery percentage is not available from the verified
NSE-MCP interface and cannot truthfully be reconstructed from yfinance volume.
