# SignalRelay frontend

Standalone Next.js dashboard extracted from the original Lovable deployment.

## Local development

Copy `.env.example` to `.env.local`, set the server-only API token, then run:

```bash
npm install
npm run dev
```

The browser calls local API routes. Those routes forward requests to the SignalRelay FastAPI service and keep `SIGNALRELAY_API_TOKEN` out of client code.

## Production variables

- `SIGNALRELAY_API_URL=https://signalrelay.vercel.app`
- `SIGNALRELAY_API_TOKEN=<server-only token accepted by the backend>`
