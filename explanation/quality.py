"""Deterministic evidence gate: validates our handling of trusted NSE data."""
from __future__ import annotations

import math

from .models import EvidenceBundle, EvidenceQualityCheck

_TRUSTED_PREFIXES = ("nse-mcp:", "rule:")
_RETRYABLE_MARKERS = ("timeout", "timed out", "connection", "temporar", "rate limit", "429", "503", "stale")


def _is_retryable_source_error(error: str) -> bool:
    return any(marker in error.lower() for marker in _RETRYABLE_MARKERS)


def check_evidence(evidence: EvidenceBundle, source_errors: tuple[str, ...] = ()) -> EvidenceQualityCheck:
    """Fail closed for missing, malformed, stale, or untraceable evidence.

    NSE-MCP/NSE is treated as the upstream authority. This gate verifies that
    *our* pipeline received and represented sufficient, traceable data; it does
    not claim to independently audit NSE's market records.
    """
    reasons: list[str] = []
    facts = evidence.facts + evidence.contextual_metrics + evidence.events
    if not evidence.facts:
        reasons.append("No rule facts were supplied for the signal.")
    for fact in facts:
        if not fact.statement.strip():
            reasons.append(f"Evidence item {fact.id} has no statement.")
        if not fact.source.startswith(_TRUSTED_PREFIXES):
            reasons.append(f"Evidence item {fact.id} has an unrecognized source: {fact.source}.")
        if any(not math.isfinite(value) for value in fact.numeric_values):
            reasons.append(f"Evidence item {fact.id} contains a non-finite numeric value.")
    reasons.extend(error for error in source_errors if error)
    return EvidenceQualityCheck(not reasons, tuple(reasons), bool(source_errors) and all(_is_retryable_source_error(error) for error in source_errors))
