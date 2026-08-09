# Project: SignalRelay MCP Server (a reasoning-layer MCP server built on NSE-MCP)

## 1. What we're building, in one paragraph

A **new, published MCP server** — called `SignalRelay` — that exposes
higher-level reasoning tools like `get_signalrelay_signal(symbol)` and
`get_explained_report(symbol)`. Internally, it composes the existing
open-source NSE-MCP server (by manitgupta) as a dependency for raw data
(quotes, bulk deals, insider trading, FII/DII flows), and adds its own
LangGraph-based agent on top that detects multi-signal patterns and
generates plain-language, citation-verified explanations. This means:
(a) you inherit NSE-MCP's already-solved handling of NSE's bot detection
/ 403 issues instead of re-fighting that battle yourself, and (b) you
still get to legitimately claim "I built and published an MCP server" —
just one layer higher in the stack, exposing reasoning instead of raw
data, which is a more differentiated thing to have built than a
data-only server.

**Resume framing:** "Built and published `SignalRelay`, an MCP server
that composes an existing open-source Indian market-data MCP server and
adds a LangGraph reasoning/explanation layer with citation-verified,
hallucination-resistant output — exposing synthesized institutional-activity
activity' analysis as new MCP tools for any agent to call."

---

## 2. Honest positioning (read this before you start)

- **Do NOT market this as "the first NSE MCP server."** It isn't. NSE-MCP
  (github.com/manitgupta/NSE-MCP) and OpenInsider-MCP already exist —
  reference them honestly in your README as prior art / dependencies,
  the way the original NSE-MCP author credited their own inspiration.
- **The defensible, differentiated claim is the reasoning/explanation
  layer** — nobody in this space is doing multi-signal synthesis with
  cited, plain-language output yet. That's what to emphasize in your
  README, resume, and interviews.
- **Depend on NSE-MCP rather than rebuilding its data layer.** It already
  covers bulk deals, insider trading, FII/DII, and quotes. Only build a
  supplementary wrapper for genuine gaps it doesn't cover. This saves
  weeks and lets you focus on the harder, more differentiated layer.

---

## 3. Full Architecture

```
┌───────────────────────────────────────────────────┐
│  Any MCP Client (Claude Desktop, your own agent,   │
│  or ANY third-party developer's agent)             │
└───────────────────────┬─────────────────────────────┘
                        │ MCP protocol
┌───────────────────────▼─────────────────────────────┐
│   YOUR NEW MCP SERVER: SignalRelay                   │
│   Exposes tools:                                     │
│     - get_signalrelay_signal(symbol)                 │
│     - get_explained_report(symbol)                   │
│                                                       │
│   Internally, each tool call runs:                   │
│   ┌─────────────────────────────────────────────┐   │
│   │  Internal Reasoning Pipeline                 │   │
│   │                                               │   │
│   │  Raw Data Fetch                               │   │
│   │        ↓                                      │   │
│   │  Feature Engineering                          │   │
│   │        ↓                                      │   │
│   │  Event Detection                              │   │
│   │        ↓                                      │   │
│   │  Rule Engine                                  │   │
│   │        ↓                                      │   │
│   │  Evidence Builder                             │   │
│   │        ↓                                      │   │
│   │  LLM Explanation                              │   │
│   │        ↓                                      │   │
│   │  Fact Verification                            │   │
│   │        ↓                                      │   │
│   │  Structured Report Output                     │   │
│   └───────────────────┬─────────────────────────────┘   │
└───────────────────────┼───────────────────────────────┘
                        │ MCP client calls (internal)
┌───────────────────────▼─────────────────────────────┐
│   NSE-MCP (existing open-source server, pinned      │
│   dependency) + thin yfinance wrapper for any gaps  │
│   Tools used: get_quote, get_bulk_deals,             │
│   get_insider_trading, get_fii_dii_flows,            │
│   get_delivery_percentage                            │
│   corporate actions / event sources                  │
└───────────────────────┬─────────────────────────────┘
                        │
                  NSE unofficial API / yfinance
```

**Key point**: your server is BOTH an MCP client (it calls NSE-MCP
internally) AND an MCP server (it exposes its own tools to the outside
world). This dual role is normal and common in MCP architectures — don't
let this confuse the implementation, it's just two separate protocol
roles happening in the same codebase.

---

## 4. Tech stack

- **Language**: Python 3.11+
- **Data layer**: NSE-MCP (existing, as a pinned dependency) + `yfinance`
  for any gaps
- **Agent orchestration**: LangGraph (reusing patterns from your NOC
  project — stateful graph, conditional edges)
- **Reasoning/LLM**: Claude API
- **Verification pattern**: a dedicated "citation-check" node in the graph
  that re-reads raw tool outputs and confirms every sentence in the draft
  explanation is traceable to a specific data point before final output
- **Frontend**: Lovable-generated dashboard — shows the report + an
  expandable "source data" view per claim
- **Testing**: `pytest` with mocked tool outputs for reproducible tests
  (don't depend on live NSE data for CI)

---

## 5. Phase-by-Phase Build Plan

### Phase 0 — Setup & scoping (2-3 days)
- [ ] Install and test NSE-MCP directly — confirm which tools work
      reliably (bulk deals, insider trading, FII/DII, quotes)
- [ ] Identify any data gaps NSE-MCP doesn't cover (e.g. historical
      delivery percentage trend) — decide whether to patch these
      yourself or drop them from scope
- [ ] Assume upfront (verify in Phase 0, don't wait to discover) that
      NSE-MCP is stock-symbol-scoped and does NOT cover broad index-level
      data (e.g. Nifty 50). Default to sourcing index levels from
      `yfinance` using `^NSEI` from day one — add this as a 6th line item
      in `data_gaps.md` alongside the original 5 data needs
- [ ] Lock the exact signal-combination rules you'll implement in
      Phase 2 — write them down now, don't leave this vague

### Phase 1 — Data access layer + your own MCP server skeleton (4-6 days)
- [ ] Wire NSE-MCP into your codebase as an internal MCP client dependency
- [ ] Build a thin supplementary wrapper only for genuine gap data,
      reusing the caching/fallback patterns from our earlier prototype
      but keeping this minimal — don't rebuild what already exists
- [ ] Scaffold your OWN MCP server (`SignalRelay`) using the `mcp`
      Python SDK, with placeholder tool definitions for
      `get_signalrelay_signal(symbol)` and `get_signalrelay_explained_report(symbol)`
      that, for now, just pass through raw data (real signal logic comes
      in Phase 2-3) — this proves the server-exposing plumbing works
      end-to-end before you add the hard reasoning logic
- [ ] Confirm your server is independently connectable — test it with
      Claude Desktop or another MCP client and confirm your placeholder
      tools show up and respond
- [ ] Write a test harness with mocked tool responses covering: normal
      data, missing data, stale/error responses
- [ ] **(Hardening)** All tool handlers are `async def`; any synchronous
      fetch (yfinance) is wrapped in `asyncio.to_thread(...)` — never call
      a blocking function directly inside an async tool handler
- [ ] **(Hardening)** All logging goes to `sys.stderr` via Python's
      `logging` module — never use bare `print()` anywhere in the
      codebase or its dependencies, since stray stdout writes corrupt the
      JSON-RPC stream back to Claude Desktop. Deliberately add a rogue
      `print()` once during testing to confirm you can recognize this
      failure mode if it happens accidentally later
- [ ] **(Hardening)** NSE-MCP subprocess uses explicitly isolated pipes
      (`stdin=subprocess.PIPE`, `stdout=subprocess.PIPE`), fully separate
      from the stdio pair your own server uses to talk to Claude Desktop
- [ ] **(Hardening)** All date fields are normalized to `datetime.date`
      (or strict ISO `YYYY-MM-DD`) at construction time inside your
      Pydantic/dataclass models — never let a raw NSE date string pass
      into the signal engine unparsed. NSE's mixed formats
      (`DD-MMM-YYYY`, `YYYY-MM-DD`, etc.) will otherwise cause "same day"
      checks to silently fail (return zero signals, no error)
- [ ] **(Hardening)** All "same day" / date-window comparisons are done
      in IST explicitly, not system local time — a UTC dev/CI environment
      can shift date boundaries by a day near midnight and silently break
      exact-day-match logic even after date *strings* are correctly parsed
- [ ] **(Hardening)** One central ticker-normalization function, unit
      tested, that all data_layer code routes through — NSE-MCP likely
      expects a bare symbol (`RELIANCE`), yfinance needs `.NS`
      (`RELIANCE.NS`), and the Nifty index uses `^NSEI`. Don't let each
      call site guess its own format
- [ ] **(Hardening)** A bare-minimum in-memory TTL cache for NSE-MCP
      calls, pulled forward into Phase 1 rather than deferred to later
      hardening — a single `get_signalrelay_signal` call already fans out
      into 4-5 NSE-MCP calls, and Phase 4's watchlist history view
      multiplies that further; without even basic caching you risk
      getting rate-limited/blocked during your own dev/testing loop
- [ ] **(Hardening)** Write a concurrency test: fire two overlapping tool
      calls to your server and confirm responses are correctly correlated
      by JSON-RPC request ID and returned to the right caller, not just
      matched by send/receive order


### Phase 2A — Event Detection Layer (2-3 days)

Before evaluating SignalRelay signals, detect whether recent corporate
events could explain unusual market activity. Many apparent institutional-activity
patterns are simply reactions to publicly known events.

- [ ] Earnings announcement or result declaration
- [ ] Dividend announcement
- [ ] Stock split
- [ ] Bonus issue
- [ ] Rights issue
- [ ] Merger / acquisition announcements
- [ ] Large company announcements or exchange filings (if available)

Example data model:

```python
@dataclass
class MarketEvent:
    event_type: str
    event_date: date
    description: str
    source: str
```

The event detector does not generate signals itself. It provides context
to the Rule Engine and Explanation Agent.

### Phase 2 — Signal synthesis logic (1-1.5 weeks — the hard component)
Define, in plain rules first (before any LLM involvement), what
combinations of raw data are meaningful. Suggested starting rule set
(refine with real research, don't just guess):
- [ ] **Insider-institutional divergence**: insider net selling AND
      bulk/block deal net institutional buying in the same stock within
      the same 5-trading-day window → flag as "divergent signal"
- [ ] **Delivery spike**: today's delivery % > 1.5x the 30-day average,
      combined with a bulk deal on the same day → flag as
      "accumulation/distribution signal"
- [ ] **FII/DII divergence from index**: FII net selling on a day where
      Nifty is flat/up → flag as "stock/sector-specific outflow, not
      broad risk-off" (and vice versa)
- [ ] Encode these as explicit, testable Python functions first — the LLM
      only comes in at the explanation-writing step, keeping this
      auditable and testable, not a black box

### Phase 3 — Explanation agent with citation guardrails (1 week)
- [ ] Build the LangGraph agent: input = stock symbol → tool calls fetch
      all relevant raw data → run Phase 2 signal functions → if any
      signal fires, pass raw data + signal type to LLM to write a
      plain-language explanation


### Evidence Builder

Before any LLM call, construct a structured evidence object containing
only verified facts and computed signal outputs.

```json
{
  "signal_type": "delivery_spike",
  "confidence": 0.68,
  "facts": [
    "Delivery percentage was 74.2%",
    "30-day average delivery percentage was 39.8%",
    "A bulk deal occurred on the same day"
  ],
  "events": [
    "Quarterly earnings announced one day earlier"
  ]
}
```

The LLM should generate explanations only from this evidence object and
must not infer unsupported facts from raw tool outputs.

- [ ] **(Hardening)** Add a `contextual_metrics` field to the evidence
      object (e.g. 52-week high/low, PE ratio, sector) even when these
      didn't trigger a signal — this gives the LLM enough grounded detail
      to write natural, non-robotic prose instead of terse boilerplate.
      Only include metrics that are typed, sourced, and checkable the
      same way signal facts are — don't add free-text padding that the
      verification node can't actually verify, or you reopen the
      hallucination risk Phase 3 exists to close
- [ ] **(Hardening)** Define and document an explicit numeric tolerance
      for the verification node's "near-exact match" numeric checks (e.g.
      ±1% relative or ±0.5 absolute) before building it. Without a stated
      tolerance, the node will either flag correct rounded claims
      ("about 74%" vs. raw 74.23) as unsupported, or let real drift
      through unflagged

- [ ] Build the **verification node**: after the LLM drafts an
      explanation, a second pass checks every factual claim against raw
      tool outputs (substring/value matching for numbers, LLM-based
      claim-checking for qualitative statements) — strip or flag any
      claim that can't be verified
- [ ] Output format: structured JSON with `signal_type`,
      `plain_language_explanation`, `confidence_note`, `facts`, `events`, and `sources`
      (which tool calls backed this)

### Phase 4 — Report generation + dashboard (3-5 days)
- [ ] Build a "SignalRelay Activity Report" view per stock — Lovable-
      generated frontend
- [ ] Each claim expandable to show the raw underlying data point
- [ ] Add a simple history view: past N days of flagged signals for a
      watchlist of stocks

### Phase 5 — Docs, honesty, and publishing (3-4 days)
- [ ] README must explicitly credit NSE-MCP as the data layer dependency
      and frame the project as "reasoning layer on top of existing MCP
      data servers" — never imply the data plumbing was built from
      scratch
- [ ] Include a "Limitations" section: this flags signals based on
      documented heuristics, not investment advice, not alpha generation
- [ ] Record a demo: query a real stock, show the full trace from raw
      data → signal detection → explanation → citation check
- [ ] Publish repo, post on LinkedIn framed around "added a
      hallucination-resistant reasoning layer on top of existing MCP data
      tools" — more sophisticated and honest than "I built an MCP server"

**Total realistic timeline at 15 hrs/week: ~4-5 weeks**

---

## 6. Issues you will hit, and how to tackle them

### 6.1 Signal rules feel arbitrary or too simplistic
**Fix**: Base rules on real equity-research heuristics, not pure
intuition. Zerodha Varsity has decent free content on bulk deals and
delivery-percentage interpretation — read it, base your rules on
documented reasoning, and cite sources in your README. This also
directly helps close the finance-fluency gap your senior's deck flagged,
so the effort is dual-purpose.

### 6.2 LLM explanation drifts from what the data actually shows
**Why it happens**: LLMs generalize/embellish even when told to stick to
facts.
**Fix**: This is exactly why Phase 3's verification node exists — treat
it as mandatory, not optional. Test it deliberately by feeding it drafts
with a planted false claim and confirming it catches it.

### 6.3 Confidence calibration — false signals look as confident as real ones
**Fix**: Output an explicit confidence/ambiguity note for every signal,
and be upfront in your README that these are correlational heuristics,
not validated predictive signals. Overclaiming accuracy is the fastest
way to lose credibility with a technically sharp interviewer.

### 6.4 Depending on NSE-MCP means depending on someone else's maintenance
**Fix**: Pin a specific version/commit of NSE-MCP as your dependency,
don't just point at `main`. Add a small compatibility test that runs
against the pinned version so schema drift breaks loudly, not silently.

### 6.5 Scope creep into "let's also predict price movement"
**Fix**: Explicitly out of scope — state this in your README's
Limitations section. Predictive modeling is a different, much harder,
and much more overclaimed project category.

### 6.6 "Why didn't you just build the data layer yourself" in interviews
**Fix**: Have a clean answer ready: "An existing open-source MCP server
already covered that well — rebuilding it wouldn't have added value. I
focused my engineering effort on the harder, less-solved problem of
turning raw multi-source data into grounded, cited analysis, which
required designing a verification step to prevent the LLM from
overstating what the data shows." This is a *better* answer than "I
built everything from scratch" — it shows judgment about where to spend
effort.

### 6.7 stdio protocol collision between your server and NSE-MCP
**Why it happens**: your process is simultaneously an MCP server (to
Claude Desktop) and an MCP client (to NSE-MCP). If either side's stdio
pipes aren't kept strictly separate, or if any code path writes to
`stdout` directly, the two JSON-RPC streams can corrupt each other.
**Fix**: spawn NSE-MCP with explicitly isolated pipes
(`stdin=subprocess.PIPE`, `stdout=subprocess.PIPE`); route all logging
through `logging` to `sys.stderr`; never use bare `print()` anywhere in
the codebase or a dependency.

### 6.8 Blocking calls freezing the async event loop
**Why it happens**: `yfinance` and most quick NSE-scraping code is
synchronous. Calling it directly inside an `async def` tool handler
blocks the whole event loop — every tool call hangs, which looks like
"the tool is slow" rather than "the architecture is broken."
**Fix**: force all tool handlers to be `async def`; wrap any synchronous
fetch in `await asyncio.to_thread(sync_fetch_func, symbol)`.

### 6.9 Silent date/timezone mismatches breaking "same day" rules
**Why it happens**: NSE data mixes date formats (`DD-MMM-YYYY`,
`YYYY-MM-DD`), and IST vs. UTC boundaries can shift a date by a day right
near midnight. Either issue makes exact-day-match logic (insider selling
+ institutional buying "on the same day") silently return zero signals —
no error, just no results.
**Fix**: normalize every date field to `datetime.date` inside your
Pydantic/dataclass construction layer; do all "same day"/window
comparisons in IST explicitly, never system local time.

### 6.10 Ticker format mismatches across data sources
**Why it happens**: NSE-MCP likely expects a bare symbol (`RELIANCE`),
yfinance needs `.NS` appended (`RELIANCE.NS`), and the Nifty index uses a
different convention entirely (`^NSEI`). Without central normalization
this shows up as bugs that look like missing data.
**Fix**: one central, unit-tested ticker-normalization function that all
data_layer code routes through.

### 6.11 Rate-limiting from your own call volume, not just NSE's bot detection
**Why it happens**: a single `get_signalrelay_signal` call fans out into
4-5 NSE-MCP calls; Phase 4's watchlist history view multiplies this
further (e.g. 10 stocks × several days = dozens of calls per page load).
This load profile is different from what NSE-MCP was built/tested
against as a single well-behaved client.
**Fix**: pull a bare-minimum in-memory TTL cache into Phase 1 rather than
deferring all caching to later hardening — otherwise you risk getting
rate-limited during your own dev/testing loop, before you ever reach the
planned caching phase. Also decide whether the Phase 4 history view
re-runs live or reads from stored/cached prior reports, since two LLM
calls (draft + verify) per stock per day adds up fast across a watchlist.

### 6.12 Historical test fixtures drifting or disappearing
**Why it happens**: NSE's unofficial data sources don't always retain
long historical archives of bulk-deal/insider data; a "known good" test
case that re-fetches live can silently break weeks later when the
underlying data shifts or disappears.
**Fix**: once you find good historical examples during Phase 0/2 (for
Definition of Done #1), snapshot that raw data into your pytest fixtures
immediately — don't depend on live re-fetching for regression tests.

---

## 7. Definition of "done"

1. Agent correctly fires signal rules on real historical data for at
   least 5-10 test stocks (verify manually against what actually
   happened around those dates). Once good historical examples are
   found, snapshot the raw data into pytest fixtures immediately --
   NSE's unofficial sources don't reliably retain long archives, so a
   regression test that re-fetches live can silently break later
2. Verification node demonstrably catches at least one deliberately
   planted false claim in testing
3. Every claim in a generated report is traceable to a specific tool
   call's raw output, shown in the dashboard
4. README honestly credits prior art and states limitations clearly
5. A recorded demo shows the full pipeline end-to-end on a real query
6. Event detection correctly identifies major corporate events and incorporates them into explanations when relevant

---

## 8a. Phase 0 + 1 prompt (current — build your own MCP server, not just a client)

```
PROJECT CONTEXT (read fully before doing anything):

I am building "SignalRelay" — a NEW MCP server (not just a client
script) for Indian (NSE-listed) stock market analysis. My server will
expose its own tools (get_signalrelay_signal(symbol),
get_explained_report(symbol)) to any MCP client (Claude Desktop, other
agents, other developers). Internally, my server acts as an MCP CLIENT
to an existing open-source MCP server called NSE-MCP
(github.com/manitgupta/NSE-MCP) to fetch raw data, so I don't have to
rebuild NSE data-fetching or fight NSE's bot-detection/403 issues myself
-- NSE-MCP already handles that.

So my codebase has TWO protocol roles:
1. MCP SERVER role: exposes my own tools to the outside world
2. MCP CLIENT role: internally calls NSE-MCP's tools to get raw data

FULL PROJECT SUMMARY (context only, do not build yet):
- Phase 2 will add signal-detection rules (plain Python functions, not
  LLM) that flag patterns like insider-institutional divergence,
  delivery % spikes, and FII/DII flow divergence from index movement.
- Phase 3 will add a LangGraph explanation agent: an LLM writes a
  plain-language explanation of a fired signal, and a separate
  verification node checks every claim against raw source data before
  it's returned.
- Phase 4/5 are dashboard and publishing, not relevant yet.

I am telling you this so Phase 0/1 code is structured to make Phase 2/3
easy to slot in later -- but do NOT implement Phase 2/3 logic now.

---

WHAT TO BUILD RIGHT NOW: PHASE 0 + PHASE 1 ONLY

Phase 0 — Setup & scoping:
1. Set up a Python 3.11+ project:
   /SignalRelay
     /data_layer          <- wraps NSE-MCP + any gap-filling code
     /server              <- MY OWN MCP server code goes here
     /tests
     pyproject.toml
     README.md (placeholder for now)
2. Install NSE-MCP as a dependency. Pin it to a specific commit hash
   (fetch the current latest commit hash and pin to that exact one, not
   a floating `main` reference). Do NOT reimplement its data-fetching
   tools yourself.
3. Write a short script that connects to NSE-MCP as an MCP client and
   lists all tools it actually exposes, with their real input/output
   schemas. Do not guess or assume tool names.
4. Based on that real tool list, write `data_gaps.md` listing which of
   these 5 data needs ARE and ARE NOT covered by NSE-MCP:
   a) current stock quote
   b) bulk/block deal data
   c) insider trading activity
   d) FII/DII flow data
   e) historical delivery percentage (last 30 days, for a 30-day avg)
5. Actually test a LIVE call to NSE-MCP's real data tools (not just
   schema discovery) and report whether it succeeds or gets blocked
   (403 or otherwise). Tell me the real result -- do not assume success.

Phase 1 — Data access layer + your own MCP server skeleton:
1. Write `data_layer/client.py`: wraps NSE-MCP as an internal MCP client
   for whichever of the 5 data needs it actually covers (per Phase 0
   findings). For any gap NSE-MCP does NOT cover, add a minimal thin
   `yfinance` fallback (`.NS` suffix for NSE tickers) -- keep this as
   small as possible, only covering the real gap.
2. Every function must return a clean, typed Python dataclass or
   Pydantic model, not raw dicts/strings, e.g.:
   ```
   @dataclass
   class QuoteResult:
       symbol: str
       price: float | None
       change: float | None
       pct_change: float | None
       volume: int | None
       source: str          # "nse-mcp" or "yfinance"
       is_stale: bool = False
       error: str | None = None
   ```
   Design similarly explicit, typed dataclasses for bulk deals, insider
   trades, FII/DII flows, and delivery percentage history, based on
   NSE-MCP's REAL schema discovered in Phase 0 -- do not invent fields.
3. Basic error handling only: catch NSE-MCP call failures/timeouts and
   return the dataclass with `error` set, not a raw traceback. Do NOT
   implement caching, retries, or fallback chains yet -- that is a later
   hardening step.
4. Scaffold MY OWN MCP server in `/server` using the official `mcp`
   Python SDK (stdio transport). Define two tools:
   - `get_signalrelay_signal(symbol: str)`
   - `get_explained_report(symbol: str)`
   For now, both should just call the Phase 1 data layer and return the
   raw fetched data as-is (formatted cleanly) -- NOT real signal logic
   or LLM explanations yet, that's Phase 2/3. The goal right now is just
   to prove the full round trip works: my server receives a tool call ->
   internally calls NSE-MCP -> returns clean data back through my own
   tool's response.
5. Write a short manual test: show me the exact Claude Desktop (or other
   MCP client) config JSON needed to connect to MY server, and confirm
   the two placeholder tools are visible and return real data when called.
6. Write pytest tests in `/tests` that MOCK NSE-MCP client responses (no
   live network dependency in automated tests). Cover: normal success,
   and a simulated tool-call failure, using realistic mock data shaped
   like NSE-MCP's actual discovered schema.

MANDATORY HARDENING REQUIREMENTS (build these in now, not later):
- All tool handlers must be `async def`. Any synchronous call (yfinance,
  etc.) must be wrapped in `await asyncio.to_thread(...)` -- never call a
  blocking function directly inside an async handler.
- All logging goes through Python's `logging` module directed to
  `sys.stderr`. Never use bare `print()` anywhere in this codebase or in
  how you shell out to NSE-MCP -- stray stdout writes corrupt the
  JSON-RPC stream back to Claude Desktop. Add one deliberate test that
  proves a rogue `print()` breaks the pipe, so this failure mode is
  recognizable later if it happens by accident.
- Spawn NSE-MCP as a subprocess with explicitly isolated pipes
  (`stdin=subprocess.PIPE`, `stdout=subprocess.PIPE`), fully separate
  from the stdio pair used to talk to Claude Desktop.
- Every date field must be normalized to `datetime.date` (or strict ISO
  `YYYY-MM-DD`) at construction time inside the dataclass/Pydantic model
  -- never let a raw NSE date string reach downstream code unparsed.
- Any "same day" or date-window logic must operate in IST explicitly,
  not system local time.
- Build one central, unit-tested ticker-normalization function that all
  data-fetching code routes through (bare symbol for NSE-MCP, `.NS`
  suffix for yfinance, `^NSEI` for the Nifty index) -- do not let
  individual call sites guess their own format.
- Include a bare-minimum in-memory TTL cache (even a simple dict with
  timestamps) for NSE-MCP calls in this phase -- this is not the later
  "hardening" caching step, it's a baseline needed to avoid getting
  rate-limited during your own dev/testing loop, given that a single
  signal check already fans out into several NSE-MCP calls.
- Write one concurrency test: fire two overlapping tool calls at your
  server and confirm responses are correctly correlated by JSON-RPC
  request ID, not just matched by send/receive order.
- Confirm in Phase 0 whether NSE-MCP exposes any broad index-level data
  (e.g. Nifty 50). Assume it does not, and default to `yfinance` with
  `^NSEI` for index data -- add this as a 6th line item in `data_gaps.md`.

CONSTRAINTS:
- Do not implement signal detection, LLM calls, or explanation
  generation yet -- explicitly out of scope for this request.
- Do not implement retry/fallback logic yet (the baseline TTL cache above
  is required now; broader retry/fallback hardening is still deferred).
- Do not guess NSE-MCP's tool names, schemas, or whether its live calls
  succeed -- actually connect and verify, then use only what you find.
- If NSE-MCP cannot be installed, connected to, or its live calls fail,
  STOP and report the exact error to me rather than fabricating a
  workaround or coding against an unverified assumed API.

Work in this order: Phase 0 discovery + live-call test first, show me
the real tool list, data_gaps.md, and live-call result -- then proceed
to Phase 1 implementation only after I've seen that.
```

---

## 8b. Original Phase 2+ prompt block (for later, unchanged)

```
Build a LangGraph-based agent system in Python that adds a reasoning and
explanation layer on top of an existing MCP server for Indian (NSE)
stock market data.

Context: use the existing open-source "NSE-MCP" server
(github.com/manitgupta/NSE-MCP) as the data-fetching dependency -- do NOT
rebuild its data-fetching tools from scratch. Pin a specific commit/
version of it as a dependency.

Build the following on top of it:

1. A LangGraph agent that, given a stock symbol, calls NSE-MCP tools to
   fetch: current quote, delivery percentage, bulk/block deals, insider
   trading activity, and FII/DII flow data for a relevant recent window
   (e.g. last 5-10 trading days).

2. A signal-detection module (plain Python functions, NOT LLM-based) that
   checks the fetched data against these explicit rules:
   - Insider-institutional divergence: insider net selling AND
     institutional (bulk/block deal) net buying in the same stock within
     the same 5-trading-day window
   - Delivery spike: today's delivery % > 1.5x the 30-day average,
     co-occurring with a bulk deal on the same day
   - FII/DII divergence from index: FII or DII net flow direction
     opposite to the broader index's movement on the same day
   Each rule should be a separate, independently testable function
   returning a structured signal object if triggered.

3. An LLM explanation node: when a signal fires, pass the raw supporting
   data and signal type to an LLM (via Claude API) to generate a
   plain-language explanation of what the signal means and why it might
   matter, including an explicit confidence/ambiguity note. Include a
   `contextual_metrics` field in the evidence object passed to the LLM
   (e.g. 52-week high/low, PE ratio, sector) even when these didn't
   trigger the signal, so the explanation reads naturally rather than
   robotically -- but only include metrics that are typed, sourced, and
   checkable by the verification node in step 4, not free-text padding.

4. A verification node: after the explanation is drafted, re-check every
   factual claim in it against the raw tool outputs. Numeric claims
   should be checked programmatically against an EXPLICIT stated
   tolerance (e.g. within ±1% relative or ±0.5 absolute of the source
   value -- pick and document one) rather than a vague "near-exact match"
   -- undefined tolerance means correct rounded claims get wrongly
   flagged, or real drift silently passes. Qualitative claims should be
   checked via a second LLM call whose only job is to confirm or flag
   each sentence as supported or unsupported by the provided raw data.
   Strip or flag any unsupported claims before final output.

5. Output a structured JSON report per stock: signal_type,
   plain_language_explanation, confidence_note, and a sources array
   listing which specific tool calls/data points backed the explanation.

Write pytest tests for the signal-detection functions using fabricated
mock data covering: each rule firing correctly, each rule correctly NOT
firing on normal data, and edge cases (missing data fields). Also write a
test that deliberately plants a false claim into a draft explanation and
confirms the verification node catches it.

Do not implement any price-prediction or forecasting logic -- this system
only explains and contextualizes existing historical/recent data, never
predicts future movement. State this limitation clearly in the README.

Write a README that: explains the problem, credits NSE-MCP explicitly as
the underlying data dependency, documents each signal rule and its
rationale, includes a full example report, and has a clear "Limitations"
section.
```

---

## 9. What to say in an interview / on LinkedIn about this

- **The problem**: "Raw market data (insider trades, bulk deals,
  institutional flows) is publicly available via MCP servers now, but
  nothing synthesizes it into an explanation a retail investor could
  actually use — you still have to manually cross-reference five
  different data points yourself."
- **The judgment call**: "An existing open-source MCP server already
  handled the data-fetching well, so I built on top of it instead of
  duplicating it, and focused my effort on the harder, differentiated
  problem: turning multi-signal raw data into grounded, cited analysis."
- **The hard part**: "LLMs will confidently generalize beyond what the
  data actually supports, so I built a verification step that checks
  every claim in the generated explanation against the raw source data
  before it's shown to the user — this was the core hallucination-
  guardrail design work."
- **The honesty**: "This flags correlational patterns based on documented
  analyst heuristics, not a predictive model — I was deliberate about
  not overclaiming what it can do."
