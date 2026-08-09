# Phase 0 findings — 11 July 2026

## Verified dependency

- Repository: `https://github.com/manitgupta/NSE-MCP.git`
- Pinned commit: `8fe76bc51fc2beb5013eb252592b285be8e1b5c0`
- Built entry point: `.vendor/NSE-MCP/dist/index.js`
- Discovery script: `scripts/discover_nse_mcp.mjs`

The script connected through MCP stdio and discovered 17 tools. Live calls
succeeded for `get_quote(RELIANCE)`, `get_bulk_deals(RELIANCE)`,
`get_insider_trading(RELIANCE)`, `get_fii_dii_activity(limit=2)`, and
`get_nifty_indices(name="NIFTY 50")`. Empty bulk/insider arrays are valid live
responses, not connection failures.

## Tool interface actually exposed

| Tool | Inputs |
| --- | --- |
| `get_bulk_deals`, `get_block_deals` | `symbol?`, `dealType?` (`BUY`, `SELL`, `ALL`) |
| `get_insider_trading` | `symbol?`, `fromDate?`, `toDate?` |
| `get_latest_bulk_deals` | `dealType?` |
| `get_top_bulk_buys`, `get_top_bulk_sells` | `limit?`, `symbol?` |
| `get_fii_dii_activity` | `limit?` |
| `get_nse_announcements` | `symbol?`, `daysBack?`, `limit?` |
| `get_market_status` | none |
| `get_nifty_indices` | `name?` |
| `get_top_gainers`, `get_top_losers`, `get_most_active` | `index?`, `limit?` |
| `search_by_symbol` | `symbol` (required), `daysBack?` |
| `get_quote` | `symbol` (required) |
| `get_short_selling` | `symbol?`, `limit?` |
| `get_corporate_actions` | `symbol?`, `fromDate?`, `toDate?` |

The live response fields used by Phase 1 are: quote (`price`, `previousClose`,
`volume`); bulk deal (`date`, `symbol`, `clientName`, `dealType`, `quantity`,
`price`); insider trade (`acquirerName`, `personCategory`, `sharesAcquired`,
`acquireFromDate`, `acquireToDate`, `intimationDate`); FII/DII (`date`,
`fiiNetValue`, `diiNetValue`); and index (`name`, `lastPrice`, `percentChange`).

## Required data coverage

| Data need | Verified coverage | Phase 1 decision |
| --- | --- | --- |
| Current quote | `get_quote` | Use NSE-MCP |
| Bulk/block deals | `get_bulk_deals`, `get_block_deals` | Use NSE-MCP |
| Insider activity | `get_insider_trading` | Use NSE-MCP |
| FII/DII flows | `get_fii_dii_activity` | Use NSE-MCP |
| 30-day delivery percentage | Not exposed | Return explicit unavailable result; find a legitimate provider before Phase 2 |
| Broad index data | `get_nifty_indices` | Use NSE-MCP; `^NSEI` is only a contingency fallback |

`yfinance` can provide quote and ordinary volume but **not delivery percentage**.
It is therefore not used as a deceptive replacement for a real delivery metric.

