"""A minimal LangGraph pipeline: draft -> verify -> structured report."""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .models import ClaimVerdict, EvidenceBundle, EvidenceQualityCheck, VerificationResult
from .providers import ExplanationProvider
from .quality import check_evidence
from .verify import verify_draft


class ExplanationState(TypedDict, total=False):
    evidence: EvidenceBundle
    draft: str
    verification: VerificationResult
    evidence_check: EvidenceQualityCheck
    source_errors: tuple[str, ...]
    error: str


def build_graph(provider: ExplanationProvider):
    async def draft_node(state: ExplanationState) -> ExplanationState:
        try:
            return {"draft": await provider.draft(state["evidence"])}
        except Exception as exc:
            return {"error": str(exc)}

    async def verify_node(state: ExplanationState) -> ExplanationState:
        return {"verification": await verify_draft(state["draft"], state["evidence"], provider)}

    def evidence_check_node(state: ExplanationState) -> ExplanationState:
        return {"evidence_check": check_evidence(state["evidence"], state.get("source_errors", ())) }

    def next_after_check(state: ExplanationState) -> str:
        if state.get("error"):
            return "safe_fallback"
        return "verify" if state["evidence_check"].passed else "safe_fallback"

    def safe_fallback_node(state: ExplanationState) -> ExplanationState:
        quality = state["evidence_check"]
        draft = state.get("draft", "")
        reason = state.get("error") or ("Evidence-quality gate failed: " + " ".join(quality.reasons))
        verdict = ClaimVerdict(draft, False, reason)
        return {"verification": VerificationResult(None, (draft,) if draft else (), (verdict,))}

    graph = StateGraph(ExplanationState)
    graph.add_node("draft", draft_node)
    graph.add_node("evidence_check", evidence_check_node)
    graph.add_node("verify", verify_node)
    graph.add_node("safe_fallback", safe_fallback_node)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "evidence_check")
    graph.add_conditional_edges("evidence_check", next_after_check, {"verify": "verify", "safe_fallback": "safe_fallback"})
    graph.add_edge("verify", END)
    graph.add_edge("safe_fallback", END)
    return graph.compile()
