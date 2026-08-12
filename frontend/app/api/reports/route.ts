const DEFAULT_API_URL = "https://signalrelay.vercel.app";
const SYMBOL_PATTERN = /^[A-Z0-9&._-]{1,25}$/;
export async function POST(request: Request) {
  let payload: { symbol?: string; include_explanation?: boolean };
  try { payload = await request.json(); } catch { return Response.json({ detail: "Invalid JSON request." }, { status: 400 }); }
  const symbol = payload.symbol?.trim().toUpperCase() ?? "";
  if (!SYMBOL_PATTERN.test(symbol)) return Response.json({ detail: "Enter a valid NSE symbol, for example RELIANCE." }, { status: 422 });
  const token = process.env.SIGNALRELAY_API_TOKEN;
  if (!token) return Response.json({ detail: "The report service is not configured correctly." }, { status: 503 });
  const baseUrl = (process.env.SIGNALRELAY_API_URL || DEFAULT_API_URL).replace(/\/$/, "");
  try {
    const upstream = await fetch(`${baseUrl}/v1/reports`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json", "X-API-Key": token }, body: JSON.stringify({ symbol, include_explanation: Boolean(payload.include_explanation) }), cache: "no-store", signal: AbortSignal.timeout(55000) });
    const body = await upstream.text();
    const headers = new Headers({ "Content-Type": upstream.headers.get("Content-Type") || "application/json", "Cache-Control": "no-store" });
    const retryAfter = upstream.headers.get("Retry-After"); if (retryAfter) headers.set("Retry-After", retryAfter);
    return new Response(body, { status: upstream.status, headers });
  } catch { return Response.json({ detail: "Could not reach the SignalRelay API. Please retry shortly." }, { status: 502, headers: { "Cache-Control": "no-store" } }); }
}
