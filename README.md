# SignalRelay

SignalRelay is a research tool for Indian stock-market data. Give it an NSE
symbol such as `RELIANCE` or `TCS`, and it collects source-tagged market data,
applies a small set of deterministic rules, and returns a report you can
inspect.

It is designed for research—not trading advice. SignalRelay never tells a user
to buy or sell, predicts prices, or invents missing information.

## What can SignalRelay do?

For an NSE-listed symbol, SignalRelay can:

- retrieve a live quote, bulk deals, insider disclosures, FII/DII flows,
  NIFTY 50 context, and relevant corporate events through NSE-MCP;
- identify descriptive patterns such as an insider sale near a bulk-deal buy or
  FII flow moving against the NIFTY 50 on the same source date;
- return the raw evidence and the limitations behind every report;
- optionally generate a short explanation, but only after an evidence check;
- run as either a desktop MCP server or a browser-facing HTTP API.

## How the pieces fit together

```text
MCP host (Claude Desktop, etc.) ──stdio──> SignalRelay ──> NSE-MCP ──> NSE/Yahoo data

Lovable dashboard ──HTTP──> SignalRelay API ──> private NSE-MCP bridge on Vercel
```

The same signal and evidence logic is used by both paths. The MCP path is for
desktop AI hosts; the HTTP path is for a website or dashboard.

## Before you start

Install these tools:

- Python 3.11 or newer
- Node.js 20 (the project includes `.node-version`)
- pnpm, enabled with `corepack enable`
- Git

You do **not** need an Anthropic API key unless you want the optional verified
natural-language explanation feature.

## Run locally

Open PowerShell in the SignalRelay folder and run these steps.

### 1. Build the pinned NSE-MCP dependency

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_nse_mcp.ps1
```

This downloads the exact version of NSE-MCP used by SignalRelay and builds it
inside `.vendor`. It may take a few minutes the first time.

### 2. Create a Python environment and install SignalRelay

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 3. Run the automated checks

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

## Use SignalRelay as an MCP server

SignalRelay can be added to any MCP host that supports a stdio server, such as
Claude Desktop.

Add this configuration to your MCP host, replacing the paths if your project
is stored elsewhere:

```json
{
  "mcpServers": {
    "SignalRelay": {
      "command": "C:\\Users\\abhis\\Desktop\\SignalRelay\\.venv\\Scripts\\python.exe",
      "args": ["-m", "server.app"],
      "env": {
        "NODE_BINARY": "node",
        "NSE_MCP_ENTRY": "C:\\Users\\abhis\\Desktop\\SignalRelay\\.vendor\\NSE-MCP\\dist\\index.js"
      }
    }
  }
}
```

Restart the MCP host after saving the configuration. It will expose two tools:

| Tool | Purpose |
| --- | --- |
| `get_signalrelay_signal(symbol)` | Deterministic signals, source-tagged evidence, events, and limitations. |
| `get_signalrelay_explained_report(symbol)` | The same report plus an optional verified explanation. |

Example prompt:

> Use `get_signalrelay_signal` for RELIANCE. Summarize the evidence and limitations without giving investment advice.

### Optional explanations

To enable `get_signalrelay_explained_report`, add this to the MCP server’s
`env` configuration:

```json
"ANTHROPIC_API_KEY": "your-server-side-key"
```

The key stays on the machine that runs the MCP server. Do not put it in a
browser app, Git repository, or public environment variable.

## Use the HTTP API locally

Start the API:

```powershell
.venv\Scripts\python.exe -m uvicorn api.app:app --reload --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for an
interactive API page.

Create a deterministic report:

```powershell
$body = @{ symbol = "RELIANCE"; include_explanation = $false } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/reports" -Method Post -ContentType "application/json" -Body $body
```

Important endpoints:

| Endpoint | Meaning |
| --- | --- |
| `GET /health` | Confirms that the API process is running. |
| `GET /ready` | Checks that the live market-data path is available. |
| `POST /v1/reports` | Creates a deterministic or explained report. |

The API uses clear error responses:

| Status | Meaning |
| --- | --- |
| `422` | The ticker format is invalid. |
| `404` | The ticker looks valid but was not found on NSE. |
| `429` | Too many requests; wait for the `Retry-After` time. |
| `503` | A required market-data dependency is temporarily unavailable. |

## Connect a frontend

The dashboard should call `POST /v1/reports` with:

```json
{
  "symbol": "RELIANCE",
  "include_explanation": false
}
```

Build the UI around these response fields:

- `signals`: deterministic patterns that matched;
- `events`: corporate-event context;
- `limitations`: known gaps and safety notes;
- `source_status`: which data sources were available and the NIFTY source date;
- `raw_evidence`: source-tagged input data;
- `reports`: verified explanation output when requested;
- `evidence_retry`: whether a fresh-data retry occurred.

Never expose `SIGNALRELAY_API_TOKEN` or `ANTHROPIC_API_KEY` to a browser. For
Lovable, put a server-side Edge Function between the dashboard and SignalRelay;
that function can add the API key safely.

The complete frontend contract is in [DASHBOARD_API.md](DASHBOARD_API.md).

## Deploy the HTTP API on Vercel

SignalRelay supports Vercel without removing direct MCP support:

- direct MCP users still run `python -m server.app` over stdio;
- Vercel runs the FastAPI adapter in `api/index.py`;
- the Python Function calls a private Node Function at `/api/nse-bridge`, which
  runs the pinned NSE-MCP subprocess.

### Deploy steps

1. Push this repository to GitHub.
2. In Vercel, choose **Add New → Project** and import the repository.
3. Keep the project root at the folder containing `vercel.json` and use the
   **Other** framework preset.
4. Deploy once to obtain your Vercel URL.
5. In **Settings → Environment Variables**, add the following for Production
   and Preview:

```text
SIGNALRELAY_ALLOWED_ORIGINS=https://signal-relay-watch.lovable.app
SIGNALRELAY_API_TOKEN=<long random secret>
SIGNALRELAY_NSE_BRIDGE_TOKEN=<a different long random secret>
SIGNALRELAY_NSE_BRIDGE_URL=https://<your-vercel-domain>/api/nse-bridge
NSE_MCP_TIMEOUT_SECONDS=20
```

6. Redeploy so Vercel receives the new variables.
7. Visit `https://<your-vercel-domain>/ready`. It should return:

```json
{"status":"ready"}
```

Only add `ANTHROPIC_API_KEY` and `SIGNALRELAY_CLAUDE_MODEL` in Vercel if you
intend to enable verified explanations. Keep those values server-side.

More operational details are in [OPERATIONS.md](OPERATIONS.md).

## Configuration reference

Start from [.env.example](.env.example). Common settings are:

| Variable | Use |
| --- | --- |
| `SIGNALRELAY_HOST` / `SIGNALRELAY_PORT` | Local API host and port. |
| `SIGNALRELAY_ALLOWED_ORIGINS` | Comma-separated allowed dashboard origins. |
| `SIGNALRELAY_API_TOKEN` | Optional HTTP API secret. |
| `SIGNALRELAY_RATE_LIMIT` | Requests per rate-limit window; defaults to `60`. |
| `SIGNALRELAY_RATE_WINDOW_SECONDS` | Rate-limit window; defaults to `60`. |
| `NSE_MCP_TIMEOUT_SECONDS` | Upstream timeout; defaults to `20`. |
| `ANTHROPIC_API_KEY` | Optional explanation-provider key. |
| `SIGNALRELAY_NSE_BRIDGE_URL` | Vercel-only private Node bridge URL. |
| `SIGNALRELAY_NSE_BRIDGE_TOKEN` | Vercel-only private bridge secret. |

## Honest limitations

- SignalRelay is research software, not investment advice.
- It does not forecast price movement or claim causation from correlation.
- Delivery-percentage history is not available from the verified NSE-MCP
  interface. The delivery-spike rule is therefore disabled, rather than being
  estimated from unrelated volume data.
- Upstream market data can be delayed or temporarily unavailable. Always read
  `source_status` and `limitations` before interpreting a report.

## Project documentation

| File | Read it when you need… |
| --- | --- |
| [LEARNING_MCP.md](LEARNING_MCP.md) | A plain-language architecture walkthrough. |
| [DASHBOARD_API.md](DASHBOARD_API.md) | The frontend request/response contract. |
| [OPERATIONS.md](OPERATIONS.md) | Deployment, security, and runtime operations. |
| [PHASE_2_RULES.md](PHASE_2_RULES.md) | The exact deterministic signal rules. |
| [PHASE_3_GUARDRAILS.md](PHASE_3_GUARDRAILS.md) | Explanation and verification safeguards. |
| [data_gaps.md](data_gaps.md) | Known source-data gaps. |

## Troubleshooting

**`NSE-MCP entrypoint not found`**

Run `scripts/setup_nse_mcp.ps1` again and confirm that `NSE_MCP_ENTRY` points
to `.vendor/NSE-MCP/dist/index.js`.

**`node` is not recognized**

Install Node.js 20, open a new terminal, run `corepack enable`, then rerun the
dependency setup script.

**`/ready` returns 503 on Vercel**

Check Vercel Function logs, verify both bridge variables, and ensure
`SIGNALRELAY_NSE_BRIDGE_URL` uses the current deployed Vercel domain.
