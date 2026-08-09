"""Model adapters: Claude is optional; tests use a controlled in-memory provider."""
from __future__ import annotations

import json
import os
from typing import Protocol

from .models import ClaimVerdict, EvidenceBundle


class ExplanationProvider(Protocol):
    async def draft(self, evidence: EvidenceBundle) -> str: ...
    async def verify_claims(self, claims: tuple[str, ...], evidence: EvidenceBundle) -> tuple[ClaimVerdict, ...]: ...


class UnavailableProvider:
    async def draft(self, evidence: EvidenceBundle) -> str:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured; no explanation was generated.")

    async def verify_claims(self, claims: tuple[str, ...], evidence: EvidenceBundle) -> tuple[ClaimVerdict, ...]:
        return tuple(ClaimVerdict(claim, False, "Verifier unavailable") for claim in claims)


class ClaudeProvider:
    def __init__(self, api_key: str, model: str | None = None) -> None:
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model or os.environ.get("SIGNALRELAY_CLAUDE_MODEL", "claude-sonnet-4-20250514")

    @staticmethod
    def _evidence_text(evidence: EvidenceBundle) -> str:
        facts = evidence.facts + evidence.contextual_metrics + evidence.events
        return "\n".join(f"[{fact.id}; {fact.source}] {fact.statement}" for fact in facts)

    async def draft(self, evidence: EvidenceBundle) -> str:
        prompt = (
            "Write a concise, non-predictive market-analysis explanation using ONLY the evidence below. "
            "Do not add facts, causal reasons, investment advice, or a price forecast. "
            "State uncertainty from the confidence note.\n\nEVIDENCE:\n" + self._evidence_text(evidence)
        )
        response = await self.client.messages.create(model=self.model, max_tokens=350, messages=[{"role": "user", "content": prompt}])
        return "".join(block.text for block in response.content if block.type == "text").strip()

    async def verify_claims(self, claims: tuple[str, ...], evidence: EvidenceBundle) -> tuple[ClaimVerdict, ...]:
        prompt = (
            "For every claim, decide whether it is directly supported by the evidence. "
            "Return ONLY a JSON array with objects: claim, supported (boolean), reason. "
            "Unsupported inference, causation, advice, and forecast claims must be false.\n\nEVIDENCE:\n"
            + self._evidence_text(evidence)
            + "\n\nCLAIMS:\n" + json.dumps(claims)
        )
        response = await self.client.messages.create(model=self.model, max_tokens=500, messages=[{"role": "user", "content": prompt}])
        raw = "".join(block.text for block in response.content if block.type == "text").strip()
        try:
            items = json.loads(raw)
            return tuple(ClaimVerdict(str(item["claim"]), bool(item["supported"]), str(item.get("reason", ""))) for item in items)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return tuple(ClaimVerdict(claim, False, f"Verifier returned invalid JSON: {exc}") for claim in claims)


def configured_provider() -> ExplanationProvider:
    key = os.environ.get("ANTHROPIC_API_KEY")
    return ClaudeProvider(key) if key else UnavailableProvider()
