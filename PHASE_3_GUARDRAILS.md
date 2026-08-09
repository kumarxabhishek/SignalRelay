# Phase 3 explanation guardrails

## Flow

```text
typed source data -> deterministic signal -> evidence builder -> Claude draft
-> conditional evidence-quality gate -> numeric verifier -> independent Claude
claim check -> cleaned report
```

The model receives only `EvidenceBundle` facts, contextual metrics, and
classified disclosed events. It never receives unrestricted raw web content or
instructions to make a trading recommendation.

## Verification rules

1. After drafting, the evidence-quality gate confirms that the required
   NSE-MCP sources succeeded, facts are non-empty, sources are recognized,
   values are finite, and evidence is traceable. It trusts NSE as the upstream
   authority; it checks our pipeline's handling of that data.
2. If this gate fails, the graph routes to a safe fallback and withholds the
   explanation. It never asks an LLM to fill in missing data.
3. Every accepted draft is split into sentence-level claims.
4. A numeric claim is accepted only when each stated number matches a sourced
   evidence value within **±0.5 absolute OR ±1% relative**.
5. A second Claude call independently marks every sentence supported or
   unsupported against the same evidence.
6. A sentence is returned only when both checks pass. Unsupported sentences are
   listed in `removed_claims`; an empty verified explanation is an acceptable,
   safer outcome.

## Key handling and safe failure

`ANTHROPIC_API_KEY` is read only from the process environment and is never
written to a file, returned by a tool, or included in logs. Without it,
`get_explained_report` returns a structured no-key error. No mock explanation
is presented as an LLM result.

## Limits

- The verifier reduces unsupported claims; it cannot prove financial insight or
  make the signal predictive.
- A passed numerical check does not validate a causal interpretation.
- The underlying signals remain correlational heuristics and are not investment
  advice.

## Fresh-data retry policy

For transient required-source failures only (timeouts, temporary connection
errors, rate limits, service errors, or stale data), the complete request path
is restarted once: local cached results are cleared, data is re-fetched, signals
are recalculated, and the draft/check/verification path runs again. A second
failure returns the safe fallback with `retry_exhausted: true`. Schema,
provenance, and malformed-data failures do not retry because a repeat cannot
repair them.
