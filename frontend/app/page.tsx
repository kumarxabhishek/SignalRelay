"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type SourceStatus = { available?: boolean; status?: string; error?: string | null; as_of?: string | null };
type Quote = { symbol?: string; price?: number | null; change?: number | null; pct_change?: number | null; volume?: number | null; source?: string };
type Flow = { date?: string; fii_net_value?: number | null; dii_net_value?: number | null };
type IndexSnapshot = { name?: string; as_of?: string; last_price?: number | null; pct_change?: number | null };
type MarketEvent = { event_type?: string; event_date?: string | null; description?: string; source?: string };
type Report = {
  phase?: number; signals?: Array<Record<string, unknown>>; reports?: Array<Record<string, unknown>>;
  events?: MarketEvent[]; limitations?: string[]; message?: string | null;
  raw_evidence?: {
    quote?: Quote; bulk_deals?: { deals?: Record<string, unknown>[]; error?: string | null };
    insider_trades?: { trades?: Record<string, unknown>[]; error?: string | null };
    fii_dii_flows?: { flows?: Flow[]; error?: string | null };
    nifty_50?: { index?: IndexSnapshot | null; error?: string | null };
    market_events?: { events?: MarketEvent[]; error?: string | null };
  };
  source_status?: Record<string, SourceStatus>;
};

const QUICK_SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"];
const SOURCE_LABELS: Record<string, string> = { quote: "Quote", bulk_deals: "Bulk deals", insider_trades: "Insider trades", fii_dii_flows: "FII/DII flows", nifty_50: "NIFTY 50", market_events: "Market events" };
const SYMBOL_PATTERN = /^[A-Z0-9&._-]{1,25}$/;

function formatMoney(value?: number | null) {
  return value == null ? "Unavailable" : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
}
function formatNumber(value?: number | null) { return value == null ? "Unavailable" : new Intl.NumberFormat("en-IN").format(value); }
function formatDate(value?: string | null) {
  if (!value) return "Date unavailable";
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.valueOf()) ? value : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(parsed);
}
function statusText(status?: SourceStatus) { if (!status) return "Unavailable"; if (status.status === "partial") return "Partial"; return status.available ? "Available" : "Unavailable"; }
function ApiMessage({ message, tone = "error" }: { message: string; tone?: "error" | "info" }) { return <div className={`notice notice-${tone}`} role={tone === "error" ? "alert" : "status"}>{message}</div>; }

export default function Home() {
  const [symbol, setSymbol] = useState("");
  const [includeExplanation, setIncludeExplanation] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<"checking" | "ready" | "unavailable">("checking");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [requestedSymbol, setRequestedSymbol] = useState("");
  const [generatedAt, setGeneratedAt] = useState<Date | null>(null);
  const [activeTab, setActiveTab] = useState<"report" | "evidence" | "audit">("report");

  useEffect(() => {
    let active = true;
    fetch("/api/health", { cache: "no-store" }).then((response) => { if (active) setServiceStatus(response.ok ? "ready" : "unavailable"); }).catch(() => { if (active) setServiceStatus("unavailable"); });
    return () => { active = false; };
  }, []);

  const runAnalysis = useCallback(async (value: string) => {
    const clean = value.trim().toUpperCase();
    setSymbol(clean); setError(null);
    if (!SYMBOL_PATTERN.test(clean)) { setError("Enter a valid NSE symbol, for example RELIANCE."); return; }
    setLoading(true); setActiveTab("report");
    try {
      const response = await fetch("/api/reports", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ symbol: clean, include_explanation: includeExplanation }) });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const fallback: Record<number, string> = { 400: "Enter a valid NSE symbol, for example RELIANCE.", 401: "The report service is not configured correctly.", 404: `No NSE-listed symbol was found for ${clean}. Check the ticker and try again.`, 429: "Too many requests. Please retry shortly.", 502: "Could not reach the SignalRelay API. Please retry shortly.", 503: "Live market data is temporarily unavailable. Please retry shortly." };
        throw new Error(typeof payload.detail === "string" ? payload.detail : fallback[response.status] || "The report service could not complete this request.");
      }
      setReport(payload as Report); setRequestedSymbol(clean); setGeneratedAt(new Date()); setServiceStatus("ready");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "The report service could not complete this request."); }
    finally { setLoading(false); }
  }, [includeExplanation]);

  function submit(event: FormEvent) { event.preventDefault(); void runAnalysis(symbol); }
  const quote = report?.raw_evidence?.quote;
  const latestFlow = report?.raw_evidence?.fii_dii_flows?.flows?.[0];
  const index = report?.raw_evidence?.nifty_50?.index;
  const events = report?.events ?? report?.raw_evidence?.market_events?.events ?? [];
  const signalCount = report?.signals?.length ?? report?.reports?.length ?? 0;
  const reportType = includeExplanation ? "Verified explanation report" : "Deterministic evidence report";
  const sourceEntries = useMemo(() => Object.entries(SOURCE_LABELS), []);

  return <div className="site-shell">
    <header className="topbar"><div className="wrap topbar-inner"><h1>SignalRelay <span>— Evidence-backed NSE market research</span></h1><div className="header-badges"><span className={`status-pill status-${serviceStatus}`} role="status" aria-live="polite"><span className="status-dot" />{serviceStatus === "checking" ? "Checking service…" : serviceStatus === "ready" ? (report ? "Live data" : "Ready") : "Service unavailable"}</span><span className="research-pill">Research only — not investment advice</span></div></div></header>
    <main className="wrap main-content">
      <section className="search-section"><div className="search-copy"><h2>Inspect a stock&apos;s evidence trail</h2><p>SignalRelay surfaces descriptive, source-traceable patterns from NSE-MCP feeds. Every claim is tied to a source; uncertainty is shown, not hidden.</p></div>
        <form className="search-form" onSubmit={submit}><label className="sr-only" htmlFor="symbol-input">NSE symbol</label><input id="symbol-input" value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="Enter NSE symbol, e.g. RELIANCE" autoComplete="off" spellCheck={false} aria-invalid={Boolean(error)} /><button type="submit" disabled={loading}>{loading ? "Analyzing…" : "Analyze"}</button></form>
        <label className="check-row"><input id="include-explanation" aria-label="Include verified explanation" type="checkbox" checked={includeExplanation} onChange={(event) => setIncludeExplanation(event.target.checked)} /><span><strong>Include verified explanation</strong><small>Uses an additional evidence-verification step; never provides investment advice.</small></span></label>
        <div className="quick-symbols" aria-label="Quick symbols">{QUICK_SYMBOLS.map((item) => <button key={item} type="button" disabled={loading} onClick={() => void runAnalysis(item)}>{item}</button>)}</div>
      </section>
      {error && <ApiMessage message={error} />}
      {!report && !loading && !error && <section className="empty-card"><p>Search an NSE symbol to view its evidence-backed report.</p><span>Every claim is shown with its backend source.</span></section>}
      {loading && <section className="loading-card" aria-live="polite"><span className="spinner" /><div><strong>Building the evidence trail</strong><p>Collecting live quote, disclosures, market flows and corporate events.</p></div></section>}
      {report && !loading && <section className="report-stack">
        <div className="summary-grid"><article><span>Symbol</span><strong>{requestedSymbol}</strong></article><article><span>Report type</span><strong>{reportType}</strong></article><article><span>Signals detected</span><strong>{signalCount}</strong></article><article><span>Generated</span><strong>{generatedAt ? generatedAt.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—"}</strong></article></div>
        {signalCount === 0 && <ApiMessage tone="info" message={`No configured rule matched ${requestedSymbol} in the current window. This is not an error — evidence, market context and corporate events remain available below.`} />}
        <section className="panel status-panel"><div className="panel-title"><div><p className="eyebrow">Upstream sources</p><h3>Data status</h3></div><span>{sourceEntries.filter(([key]) => report.source_status?.[key]?.available).length}/{sourceEntries.length} available</span></div><div className="source-grid">{sourceEntries.map(([key, label]) => { const item = report.source_status?.[key]; const state = statusText(item); return <div className="source-item" key={key}><div><strong>{label}</strong>{item?.error && <small>{item.error}</small>}</div><span className={`source-state state-${state.toLowerCase()}`}>{state}</span></div>; })}</div></section>
        <div className="tabs" role="tablist" aria-label="Report views">{(["report", "evidence", "audit"] as const).map((tab) => <button key={tab} role="tab" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)}>{tab === "report" ? "Report" : tab === "evidence" ? "Evidence" : "Audit details"}</button>)}</div>
        {activeTab === "report" && <div role="tabpanel" className="tab-panel">
          <section className="panel"><div className="panel-title"><div><p className="eyebrow">Live snapshot</p><h3>Market context</h3></div><span>Source: {quote?.source?.toUpperCase() || "NSE-MCP"}</span></div><div className="metrics-grid"><article><span>Last price</span><strong>{formatMoney(quote?.price)}</strong></article><article><span>Change</span><strong className={(quote?.change ?? 0) >= 0 ? "positive" : "negative"}>{formatMoney(quote?.change)}</strong><small>{quote?.pct_change == null ? "Unavailable" : `${quote.pct_change >= 0 ? "+" : ""}${quote.pct_change.toFixed(2)}%`}</small></article><article><span>Volume</span><strong>{formatNumber(quote?.volume)}</strong></article><article><span>NIFTY 50</span><strong>{formatNumber(index?.last_price)}</strong></article><article><span>NIFTY 50 change</span><strong>{index?.pct_change == null ? "Unavailable" : `${index.pct_change.toFixed(2)}%`}</strong></article><article><span>FII net (₹ Cr)</span><strong>{formatNumber(latestFlow?.fii_net_value)}</strong></article><article><span>DII net (₹ Cr)</span><strong>{formatNumber(latestFlow?.dii_net_value)}</strong></article><article><span>Delivery %</span><strong>Withheld</strong><small>No verified source feed currently supports this metric.</small></article></div></section>
          <section className="panel"><div className="panel-title"><div><p className="eyebrow">Source-linked disclosures</p><h3>Corporate-event timeline</h3></div><span>{events.length} event{events.length === 1 ? "" : "s"}</span></div>{events.length ? <div className="timeline">{events.map((event, indexValue) => <article key={`${event.event_date}-${indexValue}`}><span className="timeline-dot"/><div><div className="event-meta"><strong>{event.event_type || "other"}</strong><span>{formatDate(event.event_date)}</span></div><p>{event.description || "No description supplied."}</p><small>Source: {event.source || "nse-mcp"}</small></div></article>)}</div> : <p className="muted-copy">No corporate events were returned for the current window.</p>}</section>
          <section className="safety-card"><div><p className="eyebrow">Limitations & safety</p><h3>Read the evidence, not a prediction</h3><p>This report describes correlational, source-traceable activity. It does not predict prices or provide investment advice.</p></div>{report.limitations?.length ? <ul>{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul> : null}</section>
        </div>}
        {activeTab === "evidence" && <div role="tabpanel" className="tab-panel evidence-grid"><section className="panel"><div className="panel-title"><div><p className="eyebrow">Observed records</p><h3>Bulk deals</h3></div><span>{report.raw_evidence?.bulk_deals?.deals?.length ?? 0}</span></div><pre>{JSON.stringify(report.raw_evidence?.bulk_deals ?? {}, null, 2)}</pre></section><section className="panel"><div className="panel-title"><div><p className="eyebrow">Observed records</p><h3>Insider trades</h3></div><span>{report.raw_evidence?.insider_trades?.trades?.length ?? 0}</span></div><pre>{JSON.stringify(report.raw_evidence?.insider_trades ?? {}, null, 2)}</pre></section></div>}
        {activeTab === "audit" && <div role="tabpanel" className="tab-panel"><section className="panel"><div className="panel-title"><div><p className="eyebrow">Machine-readable output</p><h3>Complete report payload</h3></div><span>Phase {report.phase ?? "—"}</span></div><pre className="audit-json">{JSON.stringify(report, null, 2)}</pre></section></div>}
      </section>}
    </main>
    <footer><div className="wrap"><p>SignalRelay · Research software · Not investment advice</p><p>Built by <a href="https://www.linkedin.com/in/abhishek-kumar-42a2a024a/" target="_blank" rel="noreferrer">Abhishek Kumar</a></p></div></footer>
  </div>;
}
