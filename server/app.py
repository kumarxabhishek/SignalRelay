"""Public MCP tools for deterministic signals and verified explanations."""
from __future__ import annotations

import asyncio
import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from data_layer.client import NseDataClient, report_to_dict
from explanation.evidence import build_evidence
from explanation.graph import build_graph
from explanation.models import ExplainedSignalReport, VerificationResult
from explanation.providers import configured_provider
from explanation.retry import run_with_one_fresh_retry
from server.errors import MarketDataUnavailableError, UnknownNseSymbolError
from signals.events import detected_events
from signals.rules import (
    detect_fii_index_divergence,
    detect_insider_bulk_divergence,
)

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)
mcp = FastMCP("SignalRelay")
client = NseDataClient()

_UNKNOWN_SYMBOL_MARKERS = (
    "not found", "no data", "possibly delisted", "invalid symbol", "quote not found",
    # NSE-MCP's pinned Yahoo adapter currently throws this for a missing ticker.
    "cannot read properties of undefined (reading 'symbol')",
)


async def _validated_quote(symbol: str):
    """Stop typos from being misrepresented downstream as a no-signal result."""
    quote = await client.get_quote(symbol)
    error = quote.error or ""
    if quote.price is not None:
        return quote
    if not error or any(marker in error.lower() for marker in _UNKNOWN_SYMBOL_MARKERS):
        raise UnknownNseSymbolError(
            f"No NSE-listed symbol was found for '{quote.symbol}'. Check the ticker and try again.",
        )
    raise MarketDataUnavailableError("The live quote source is currently unavailable. Try again shortly.")


async def _phase_two_data(symbol: str, *, force_refresh: bool = False) -> dict[str, object]:
    if force_refresh:
        await client.clear_cache()
    quote = await _validated_quote(symbol)
    deals, insiders, flows, delivery, index, events = await asyncio.gather(
        client.get_bulk_deals(symbol), client.get_insider_trades(symbol),
        client.get_fii_dii_flows(), client.get_delivery_history(symbol), client.get_nifty_50_snapshot(),
        client.get_market_events(symbol),
    )
    candidates = (
        detect_insider_bulk_divergence(insiders, deals),
        detect_fii_index_divergence(flows, index.index),
    )
    signals = tuple(candidate for candidate in candidates if candidate is not None)
    return {
        "phase": 2,
        "signals": signals,
        "events": detected_events(events.events),
        "limitations": [
            delivery.error,
            "Delivery-spike detection is disabled until a verified delivery-percentage history source is integrated.",
        ] if delivery.error else [],
        "raw_evidence": {"quote": quote, "bulk_deals": deals, "insider_trades": insiders, "fii_dii_flows": flows, "nifty_50": index, "market_events": events},
        "source_status": {
            "quote": {"available": quote.error is None, "error": quote.error},
            "bulk_deals": {"available": deals.error is None, "error": deals.error},
            "insider_trades": {"available": insiders.error is None, "error": insiders.error},
            "fii_dii_flows": {"available": flows.error is None, "error": flows.error},
            "nifty_50": {"available": index.error is None, "as_of": index.index.as_of if index.index else None, "error": index.error},
            "market_events": {"available": events.error is None, "error": events.error},
        },
    }


async def build_signal_report(symbol: str) -> str:
    return json.dumps(report_to_dict(await _phase_two_data(symbol)), indent=2)


async def _phase_three_attempt(symbol: str, *, force_refresh: bool) -> tuple[dict[str, object], bool]:
    phase_two = await _phase_two_data(symbol, force_refresh=force_refresh)
    signals = phase_two["signals"]
    assert isinstance(signals, tuple)
    raw_evidence = phase_two["raw_evidence"]
    assert isinstance(raw_evidence, dict)
    quote = raw_evidence["quote"]
    events = phase_two["events"]
    provider = configured_provider()
    graph = build_graph(provider)
    reports: list[ExplainedSignalReport] = []
    for signal in signals:
        required = {
            "insider_bulk_divergence": (raw_evidence["insider_trades"], raw_evidence["bulk_deals"]),
            "fii_index_divergence": (raw_evidence["fii_dii_flows"], raw_evidence["nifty_50"]),
        }[signal.signal_type]
        source_errors = tuple(result.error for result in required if result.error)
        evidence = build_evidence(symbol, signal, quote, events, source_errors=source_errors)
        state = await graph.ainvoke({"evidence": evidence, "source_errors": source_errors})
        verification = state.get("verification", VerificationResult(None, (), ()))
        evidence_check = state["evidence_check"]
        error = state.get("error")
        if not evidence_check.passed:
            error = "Explanation withheld: " + " ".join(evidence_check.reasons)
        reports.append(ExplainedSignalReport(
            signal.signal_type,
            verification.verified_explanation,
            signal.confidence_note,
            evidence.facts,
            evidence.events,
            tuple(sorted({fact.source for fact in evidence.facts + evidence.contextual_metrics + evidence.events})),
            verification,
            evidence_check,
            error,
        ))
    retryable_failure = any(not report.evidence_check.passed and report.evidence_check.retryable for report in reports)
    return {
        "phase": 3,
        "reports": reports,
        "message": "No configured signal fired." if not reports else None,
        "limitations": phase_two["limitations"],
        "raw_evidence": raw_evidence,
        "source_status": phase_two["source_status"],
    }, retryable_failure


async def build_explained_report(symbol: str) -> str:
    outcome = await run_with_one_fresh_retry(
        lambda force_refresh: _phase_three_attempt(symbol, force_refresh=force_refresh),
    )
    report = outcome.value
    report["evidence_retry"] = {
        "attempts": outcome.attempts,
        "fresh_data_retry_performed": outcome.retried,
        "retry_exhausted": outcome.exhausted,
    }
    return json.dumps(report_to_dict(report), indent=2)


@mcp.tool()
async def get_signalrelay_signal(symbol: str) -> str:
    """Return deterministic Phase 2 signals and source-tagged raw evidence."""
    return await build_signal_report(symbol)


@mcp.tool()
async def get_signalrelay_explained_report(symbol: str) -> str:
    """Return an evidence-grounded explanation only after verification."""
    return await build_explained_report(symbol)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
