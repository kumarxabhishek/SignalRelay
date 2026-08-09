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
- run as a desktop MCP server through any compatible MCP host.

## How the pieces fit together

```text
MCP host (Claude Desktop, etc.) ──stdio──> SignalRelay ──> NSE-MCP ──> NSE/Yahoo data
```

SignalRelay runs locally as an MCP server. Your MCP host starts it and sends
requests through standard input/output.

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

## Honest limitations

- SignalRelay is research software, not investment advice.
- It does not forecast price movement or claim causation from correlation.
- Delivery-percentage history is not available from the verified NSE-MCP
  interface. The delivery-spike rule is therefore disabled, rather than being
  estimated from unrelated volume data.
- Upstream market data can be delayed or temporarily unavailable. Always read
  `source_status` and `limitations` before interpreting a report.

## More detail

| File | Read it when you need… |
| --- | --- |
| [LEARNING_MCP.md](LEARNING_MCP.md) | A plain-language architecture walkthrough. |
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
