from explanation.graph import build_graph
from explanation.models import ClaimVerdict, EvidenceBundle, EvidenceFact
from explanation.retry import run_with_one_fresh_retry
from explanation.verify import verify_draft


class ControlledProvider:
    def __init__(self, draft_text: str) -> None:
        self.draft_text = draft_text
        self.verify_calls = 0

    async def draft(self, evidence: EvidenceBundle) -> str:
        return self.draft_text

    async def verify_claims(self, claims: tuple[str, ...], evidence: EvidenceBundle) -> tuple[ClaimVerdict, ...]:
        self.verify_calls += 1
        return tuple(ClaimVerdict(claim, True, "Supported by the supplied evidence") for claim in claims)


def evidence() -> EvidenceBundle:
    return EvidenceBundle(
        "RELIANCE", "fii_index_divergence", 0.5, "Descriptive only.",
        (EvidenceFact("signal-1", "FII net selling was reported.", "nse-mcp:get_fii_dii_activity"),),
        (EvidenceFact("quote-price", "Latest reported price was 100.00 INR.", "nse-mcp:get_quote", (100.0,)),),
        (),
    )


async def test_numeric_verifier_strips_deliberately_planted_false_claim() -> None:
    provider = ControlledProvider("Latest reported price was 100.40 INR. The price was 999.00 INR.")
    result = await verify_draft(await provider.draft(evidence()), evidence(), provider)
    assert result.verified_explanation == "Latest reported price was 100.40 INR."
    assert result.removed_claims == ("The price was 999.00 INR.",)
    assert result.verdicts[1].reason == "Numeric value is not grounded"


async def test_langgraph_runs_draft_then_verification() -> None:
    provider = ControlledProvider("Latest reported price was 100.00 INR.")
    state = await build_graph(provider).ainvoke({"evidence": evidence()})
    assert state["verification"].verified_explanation == "Latest reported price was 100.00 INR."


async def test_quality_gate_routes_bad_source_data_to_safe_fallback() -> None:
    provider = ControlledProvider("Latest reported price was 100.00 INR.")
    state = await build_graph(provider).ainvoke({"evidence": evidence(), "source_errors": ("NSE-MCP timeout",)})
    assert state["evidence_check"].passed is False
    assert state["verification"].verified_explanation is None
    assert provider.verify_calls == 0


async def test_fresh_data_retry_is_bounded_to_two_attempts() -> None:
    attempts: list[bool] = []

    async def run_attempt(force_refresh: bool) -> tuple[str, bool]:
        attempts.append(force_refresh)
        return ("still unavailable" if force_refresh else "temporary failure", True)

    outcome = await run_with_one_fresh_retry(run_attempt)
    assert attempts == [False, True]
    assert outcome.attempts == 2
    assert outcome.retried is True and outcome.exhausted is True


async def test_non_retryable_failure_does_not_refetch_data() -> None:
    attempts: list[bool] = []

    async def run_attempt(force_refresh: bool) -> tuple[str, bool]:
        attempts.append(force_refresh)
        return "invalid schema", False

    outcome = await run_with_one_fresh_retry(run_attempt)
    assert attempts == [False]
    assert outcome.attempts == 1 and outcome.retried is False
