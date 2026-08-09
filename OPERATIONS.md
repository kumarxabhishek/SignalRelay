# Operating SignalRelay

## Local MCP host

Use the stdio configuration in [README.md](README.md). This is appropriate for
Claude Desktop and local development tools.

## Local dashboard API

1. Copy `.env.example` values into your process environment; do not commit a
   real `.env` file.
2. Run `python -m uvicorn api.app:app --reload --port 8000` from the activated
   virtual environment.
3. Visit `http://127.0.0.1:8000/docs` to inspect the generated OpenAPI contract.

## Container deployment

The included `Dockerfile` is a concrete deployment artifact for a managed
container service (for example Cloud Run, Render, or Fly.io). Build it with
`docker build -t signalrelay .`, then inject `SIGNALRELAY_API_TOKEN`,
`SIGNALRELAY_ALLOWED_ORIGINS`, and optionally `ANTHROPIC_API_KEY` through the
platform's secret store. Put the container behind the platform's HTTPS ingress
and route its readiness probe to `/ready`.

## Vercel deployment

Vercel uses `app.py` for the FastAPI adapter. Its Python Function calls
the private Node Function at `/api/nse-bridge`, which owns the NSE-MCP stdio
child process. This keeps the HTTP deployment compatible with Vercel while
preserving `python -m server.app` for direct stdio MCP clients.

Set these Vercel Production and Preview environment variables (with different
values per environment):

| Variable | Purpose |
| --- | --- |
| `SIGNALRELAY_ALLOWED_ORIGINS` | Exact Lovable dashboard origin. |
| `SIGNALRELAY_API_TOKEN` | API secret, passed only by a server-side proxy. |
| `SIGNALRELAY_NSE_BRIDGE_URL` | `https://<deployment-domain>/api/nse-bridge`. |
| `SIGNALRELAY_NSE_BRIDGE_TOKEN` | Private token used only between functions. |
| `NSE_MCP_TIMEOUT_SECONDS` | Upstream timeout; default is 20 seconds. |
| `ANTHROPIC_API_KEY` | Optional, server-side only explanation provider key. |

After every environment-variable change, redeploy. Check `/ready` and one
known-symbol `/v1/reports` request before updating the Lovable frontend URL.

## Error behavior

| Condition | API result | User-facing behavior |
| --- | --- | --- |
| Invalid characters/format | `422` | Ask for a valid NSE ticker format. |
| Valid-looking unknown ticker | `404` | “No NSE-listed symbol found”; do not show no-signal. |
| Temporary quote/upstream failure | `503` | Ask the user to retry later. |
| No configured signal | `200` | Show the normal no-signal report. |

## Deployment checklist

- Set `SIGNALRELAY_HOST=0.0.0.0` only in a managed deployment environment.
- Set `SIGNALRELAY_ALLOWED_ORIGINS` to the exact dashboard origin; never use a
  wildcard with a production dashboard.
- Set a long `SIGNALRELAY_API_TOKEN` and pass it from a Lovable Cloud/Supabase
  Edge Function, not browser code.
- Keep `ANTHROPIC_API_KEY` only in the server-side secret store.
- Health-check `GET /health`; monitor `5xx` responses and upstream failures.
- Use `GET /ready` for deployment readiness checks; it verifies the live Node →
  NSE-MCP → market-data path and returns `503` when that path is unavailable.
- Configure `NSE_MCP_TIMEOUT_SECONDS` (20 seconds by default) and enforce a
  shared rate limit at the gateway. The built-in in-memory limiter is a safe
  single-instance default, not a replacement for a distributed limiter.
- Terminate TLS at the managed ingress, forward only HTTPS traffic to clients,
  and emit structured access/error logs into your monitoring provider. Alert on
  sustained 5xx, readiness failures, and elevated 429 responses.
- Add CI for unit tests and a separately scheduled, credentialed smoke check
  against a known NSE symbol; do not make live-market availability a PR gate.
- Keep the pinned NSE-MCP version and rerun the compatibility tests when
  updating it.
