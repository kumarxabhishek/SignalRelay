from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceFact:
    id: str
    statement: str
    source: str
    numeric_values: tuple[float, ...] = ()


@dataclass(frozen=True)
class EvidenceBundle:
    symbol: str
    signal_type: str
    confidence: float
    confidence_note: str
    facts: tuple[EvidenceFact, ...]
    contextual_metrics: tuple[EvidenceFact, ...]
    events: tuple[EvidenceFact, ...]


@dataclass(frozen=True)
class ClaimVerdict:
    claim: str
    supported: bool
    reason: str


@dataclass(frozen=True)
class VerificationResult:
    verified_explanation: str | None
    removed_claims: tuple[str, ...]
    verdicts: tuple[ClaimVerdict, ...]
    numeric_tolerance: str = "±0.5 absolute OR ±1% relative"


@dataclass(frozen=True)
class EvidenceQualityCheck:
    passed: bool
    reasons: tuple[str, ...]
    retryable: bool = False


@dataclass(frozen=True)
class ExplainedSignalReport:
    signal_type: str
    plain_language_explanation: str | None
    confidence_note: str
    facts: tuple[EvidenceFact, ...]
    events: tuple[EvidenceFact, ...]
    sources: tuple[str, ...]
    verification: VerificationResult
    evidence_check: EvidenceQualityCheck
    error: str | None = None
