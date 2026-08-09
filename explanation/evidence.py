"""Build a compact, sourced fact set before any model is called."""
from __future__ import annotations

import re

from data_layer.models import MarketEvent, QuoteResult
from signals.models import Signal

from .models import EvidenceBundle, EvidenceFact

_NUMBER = re.compile(r"(?<![\w.-])-?\d+(?:\.\d+)?(?![\w.-])")


def _numbers(text: str) -> tuple[float, ...]:
    return tuple(float(value) for value in _NUMBER.findall(text))


def build_evidence(
    symbol: str,
    signal: Signal,
    quote: QuoteResult,
    events: tuple[MarketEvent, ...],
    *,
    source_errors: tuple[str, ...] = (),
) -> EvidenceBundle:
    facts = tuple(
        EvidenceFact(f"signal-{index}", statement, f"nse-mcp:derived/{signal.signal_type}", _numbers(statement))
        for index, statement in enumerate(signal.facts, start=1)
    )
    metrics: list[EvidenceFact] = []
    if quote.price is not None:
        metrics.append(EvidenceFact("quote-price", f"Latest reported price was {quote.price:.2f} INR.", "nse-mcp:get_quote", (quote.price,)))
    if quote.pct_change is not None:
        metrics.append(EvidenceFact("quote-change", f"Latest reported percentage change was {quote.pct_change:.2f}%.", "nse-mcp:get_quote", (quote.pct_change,)))
    if quote.volume is not None:
        metrics.append(EvidenceFact("quote-volume", f"Latest reported volume was {quote.volume}.", "nse-mcp:get_quote", (float(quote.volume),)))
    event_facts = tuple(
        EvidenceFact(f"event-{index}", event.description, event.source, _numbers(event.description))
        for index, event in enumerate(events, start=1)
    )
    return EvidenceBundle(symbol, signal.signal_type, signal.confidence, signal.confidence_note, facts, tuple(metrics), event_facts)
