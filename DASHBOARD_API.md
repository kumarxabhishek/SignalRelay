# Dashboard API contract

The Lovable app should call this HTTP adapter, **not** the stdio MCP process.
The adapter invokes the same Python report builders used by the MCP tools.

## Local start

```powershell
.venv\Scripts\python.exe -m uvicorn api.app:app --reload --port 8000
```

## Endpoints

`GET /health` confirms the API process is running and whether Claude explanations are
configured. It never returns secrets. `GET /ready` performs a live NSE-MCP quote-path
check and returns `503` while a required dependency is unavailable.

`POST /v1/reports` creates a live report.

```json
{
  "symbol": "RELIANCE",
  "include_explanation": false
}
```

Set `include_explanation` to `true` only after configuring `ANTHROPIC_API_KEY`.
The response is the Phase 2 or Phase 3 report JSON already produced by the MCP.
Important fields for the dashboard are `signals`, `events`, `limitations`,
`source_status`, `raw_evidence`, `reports`, and `evidence_retry`. Render
`source_status` beside results as a data-freshness/source-status panel, rather than
hiding partial upstream failures.

### Search errors

Do not render an error response as a no-signal report:

- `422`: invalid ticker format.
- `404`: valid-looking ticker was not found on NSE; show the API message and
  retain the user’s search text for correction.
- `503`: upstream market data is temporarily unavailable; offer a retry.
- `429`: request limit reached; honor the `Retry-After` header before retrying.

## Lovable integration

For local development, configure Lovable to call `http://localhost:8000` only if
the preview can reach your machine. For a deployed dashboard, deploy this API
first, set `SIGNALRELAY_ALLOWED_ORIGINS` to the exact Lovable domain, and use
`SIGNALRELAY_API_TOKEN` through a Lovable Cloud/Supabase Edge Function. Never
place `ANTHROPIC_API_KEY` or `SIGNALRELAY_API_TOKEN` in browser code.
