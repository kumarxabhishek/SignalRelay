"""Programmatic numeric checks precede the qualitative LLM claim check."""
from __future__ import annotations

import re

from .models import ClaimVerdict, EvidenceBundle, VerificationResult
from .providers import ExplanationProvider

NUMBER = re.compile(r"(?<![\w.-])-?\d+(?:\.\d+)?(?![\w.-])")


def split_claims(draft: str) -> tuple[str, ...]:
    return tuple(sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", draft.strip()) if sentence.strip())


def numeric_claim_is_supported(claim: str, evidence: EvidenceBundle) -> bool:
    numbers = [float(match) for match in NUMBER.findall(claim)]
    if not numbers:
        return True
    supported = [number for fact in evidence.facts + evidence.contextual_metrics + evidence.events for number in fact.numeric_values]
    return all(any(abs(value - source) <= 0.5 or abs(value - source) <= max(abs(source) * 0.01, 0.01) for source in supported) for value in numbers)


async def verify_draft(draft: str, evidence: EvidenceBundle, provider: ExplanationProvider) -> VerificationResult:
    claims = split_claims(draft)
    numeric_valid = {claim: numeric_claim_is_supported(claim, evidence) for claim in claims}
    qualitative = {verdict.claim: verdict for verdict in await provider.verify_claims(claims, evidence)}
    verdicts: list[ClaimVerdict] = []
    kept: list[str] = []
    removed: list[str] = []
    for claim in claims:
        verdict = qualitative.get(claim, ClaimVerdict(claim, False, "No verifier verdict returned"))
        if numeric_valid[claim] and verdict.supported:
            kept.append(claim)
            verdicts.append(verdict)
        else:
            reason = verdict.reason if not numeric_valid[claim] else verdict.reason
            verdicts.append(ClaimVerdict(claim, False, "Numeric value is not grounded" if not numeric_valid[claim] else reason))
            removed.append(claim)
    return VerificationResult(" ".join(kept) or None, tuple(removed), tuple(verdicts))
