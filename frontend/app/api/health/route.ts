const DEFAULT_API_URL = "https://signalrelay.vercel.app";
function apiUrl(path: string) { return `${(process.env.SIGNALRELAY_API_URL || DEFAULT_API_URL).replace(/\/$/, "")}${path}`; }
export async function GET() {
  try {
    const response = await fetch(apiUrl("/health"), { cache: "no-store", signal: AbortSignal.timeout(10000) });
    const payload = await response.json().catch(() => ({ status: "unavailable" }));
    return Response.json(payload, { status: response.ok ? 200 : 503, headers: { "Cache-Control": "no-store" } });
  } catch { return Response.json({ status: "unavailable" }, { status: 503, headers: { "Cache-Control": "no-store" } }); }
}
