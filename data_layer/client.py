"""Internal MCP client. It talks to NSE-MCP through isolated child pipes."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .cache import AsyncTTLCache
from .models import (
    BulkDeal, BulkDealsResult, DeliveryHistoryResult, FiiDiiFlow, FiiDiiFlowsResult,
    IndexSnapshot, IndexSnapshotResult, InsiderTrade, InsiderTradesResult, MarketEvent,
    MarketEventsResult, QuoteResult, as_float, as_int, parse_nse_date,
)
from .symbols import normalize_nse_symbol
from signals.events import classify_event

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolTransport(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class SubprocessNseTransport:
    """Each call owns a fully isolated stdio pair for the NSE-MCP subprocess."""
    def __init__(self, entrypoint: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        self.entrypoint = entrypoint or Path(os.environ.get("NSE_MCP_ENTRY", root / ".vendor/NSE-MCP/dist/index.js"))
        self.wrapper = root / "scripts" / "nse_mcp_stdio_wrapper.mjs"
        self.node = os.environ.get("NODE_BINARY", "node")

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if not self.entrypoint.is_file():
            raise RuntimeError(f"NSE-MCP entrypoint not found: {self.entrypoint}")
        # The upstream Yahoo dependency occasionally emits a non-JSON notice via
        # console.*. The wrapper sends those logs to stderr before NSE-MCP starts.
        params = StdioServerParameters(command=self.node, args=[str(self.wrapper), str(self.entrypoint)])
        timeout_seconds = float(os.environ.get("NSE_MCP_TIMEOUT_SECONDS", "20"))
        try:
            async with asyncio.timeout(timeout_seconds):
                async with stdio_client(params) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        return await session.call_tool(name, arguments)
        except TimeoutError as exc:
            raise TimeoutError(f"NSE-MCP request timed out after {timeout_seconds:g} seconds") from exc


class VercelNseBridgeTransport:
    """Calls the private Node bridge when SignalRelay runs as a Vercel Function."""
    def __init__(self, url: str, token: str | None = None) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.timeout_seconds = float(os.environ.get("NSE_MCP_TIMEOUT_SECONDS", "20"))

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        def post() -> Any:
            body = json.dumps({"name": name, "arguments": arguments}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["X-SignalRelay-Bridge-Token"] = self.token
            request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"SignalRelay NSE bridge returned HTTP {exc.code}: {detail}") from exc
            result = payload.get("result")
            if not isinstance(result, dict):
                raise RuntimeError("SignalRelay NSE bridge returned an invalid response")
            content = tuple(SimpleNamespace(**item) for item in result.get("content", []))
            return SimpleNamespace(isError=bool(result.get("isError", False)), content=content)

        try:
            return await asyncio.to_thread(post)
        except TimeoutError as exc:
            raise TimeoutError(f"SignalRelay NSE bridge timed out after {self.timeout_seconds:g} seconds") from exc


def _text_json(result: Any) -> Any:
    if getattr(result, "isError", False):
        content = getattr(result, "content", [])
        messages = [item.text for item in content if getattr(item, "type", None) == "text"]
        detail = " ".join(messages).strip()
        raise RuntimeError(detail or "NSE-MCP returned an error response")
    content = getattr(result, "content", [])
    texts = [item.text for item in content if getattr(item, "type", None) == "text"]
    if not texts:
        raise RuntimeError("NSE-MCP returned no text content")
    return json.loads(texts[0])


class NseDataClient:
    def __init__(self, transport: ToolTransport | None = None, ttl_seconds: float = 60.0) -> None:
        bridge_url = os.environ.get("SIGNALRELAY_NSE_BRIDGE_URL")
        self.transport = transport or (
            VercelNseBridgeTransport(bridge_url, os.environ.get("SIGNALRELAY_NSE_BRIDGE_TOKEN"))
            if bridge_url else SubprocessNseTransport()
        )
        self.cache: AsyncTTLCache[Any] = AsyncTTLCache(ttl_seconds)

    async def clear_cache(self) -> None:
        """Used only by the bounded Phase 3 fresh-data retry path."""
        await self.cache.clear()

    async def _call(self, name: str, arguments: dict[str, Any]) -> Any:
        key = f"{name}:{json.dumps(arguments, sort_keys=True)}"
        async def load() -> Any:
            return _text_json(await self.transport.call_tool(name, arguments))
        return await self.cache.get_or_load(key, load)

    async def get_quote(self, symbol: str) -> QuoteResult:
        clean = normalize_nse_symbol(symbol)
        try:
            raw = await self._call("get_quote", {"symbol": clean})
            # NSE-MCP adapters do not all use the same quote field names.  Keep
            # the normalized API stable while accepting the documented variants.
            previous = as_float(_first_present(raw, "previousClose", "previous_close"))
            price = as_float(_first_present(raw, "price", "lastPrice", "last_price", "currentPrice"))
            change = price - previous if price is not None and previous is not None else None
            pct = (change / previous * 100) if change is not None and previous else None
            return QuoteResult(clean, price, change, pct, as_int(_first_present(raw, "volume", "totalTradedVolume")), "nse-mcp")
        except Exception as exc:
            logger.warning("quote fetch failed for %s: %s", clean, exc)
            return QuoteResult(clean, None, None, None, None, "nse-mcp", error=str(exc))

    async def get_bulk_deals(self, symbol: str) -> BulkDealsResult:
        clean = normalize_nse_symbol(symbol)
        try:
            rows = await self._call("get_bulk_deals", {"symbol": clean})
            deals = tuple(BulkDeal(parse_nse_date(row.get("date")), clean, row.get("clientName", ""), row.get("dealType", "BUY"), as_int(row.get("quantity")), as_float(row.get("price"))) for row in rows)
            return BulkDealsResult(clean, deals, "nse-mcp")
        except Exception as exc:
            return BulkDealsResult(clean, (), "nse-mcp", str(exc))

    async def get_insider_trades(self, symbol: str) -> InsiderTradesResult:
        clean = normalize_nse_symbol(symbol)
        try:
            rows = await self._call("get_insider_trading", {"symbol": clean})
            trades = tuple(InsiderTrade(clean, row.get("acquirerName", ""), row.get("personCategory", ""), as_int(row.get("sharesAcquired")), row.get("modeOfAcquisition", ""), parse_nse_date(row.get("acquireFromDate")), parse_nse_date(row.get("acquireToDate")), parse_nse_date(row.get("intimationDate"))) for row in rows)
            return InsiderTradesResult(clean, trades, "nse-mcp")
        except Exception as exc:
            return InsiderTradesResult(clean, (), "nse-mcp", str(exc))

    async def get_fii_dii_flows(self, limit: int = 5) -> FiiDiiFlowsResult:
        try:
            rows = await self._call("get_fii_dii_activity", {"limit": limit})
            flows = tuple(FiiDiiFlow(parse_nse_date(row["date"]), as_float(row.get("fiiNetValue")), as_float(row.get("diiNetValue"))) for row in rows)
            return FiiDiiFlowsResult(flows, "nse-mcp")
        except Exception as exc:
            return FiiDiiFlowsResult((), "nse-mcp", str(exc))

    async def get_delivery_history(self, symbol: str) -> DeliveryHistoryResult:
        clean = normalize_nse_symbol(symbol)
        return DeliveryHistoryResult(clean, (), "unavailable", "NSE-MCP has no delivery-percentage-history tool; yfinance cannot supply delivery percentage.")

    async def get_nifty_50_snapshot(self) -> IndexSnapshotResult:
        try:
            rows = await self._call("get_nifty_indices", {"name": "NIFTY 50"})
            row = next((item for item in rows if item.get("name", "").upper() == "NIFTY 50"), None)
            if row is None:
                return IndexSnapshotResult(None, "nse-mcp", "NIFTY 50 was not returned by NSE-MCP")
            as_of = _source_date(row)
            if as_of is None:
                return IndexSnapshotResult(None, "nse-mcp", "NSE-MCP did not supply a NIFTY 50 source date; same-day flow comparison was withheld.")
            snapshot = IndexSnapshot("NIFTY 50", as_of, as_float(row.get("lastPrice")), as_float(row.get("percentChange")))
            return IndexSnapshotResult(snapshot, "nse-mcp")
        except Exception as exc:
            return IndexSnapshotResult(None, "nse-mcp", str(exc))

    async def get_market_events(self, symbol: str, days_back: int = 10) -> MarketEventsResult:
        clean = normalize_nse_symbol(symbol)
        try:
            announcements, actions = await asyncio.gather(
                self._call("get_nse_announcements", {"symbol": clean, "daysBack": days_back, "limit": 20}),
                self._call("get_corporate_actions", {"symbol": clean}),
            )
            events: list[MarketEvent] = []
            for item in announcements:
                description = item.get("description", "")
                event_type = classify_event(description) or "other"
                events.append(MarketEvent(event_type, parse_nse_date(item.get("broadcastDateTime")), description, "nse-mcp:get_nse_announcements"))
            for item in actions:
                description = item.get("purpose", "")
                event_type = classify_event(description) or "other"
                events.append(MarketEvent(event_type, parse_nse_date(item.get("exDate")), description, "nse-mcp:get_corporate_actions"))
            return MarketEventsResult(clean, tuple(events), "nse-mcp")
        except Exception as exc:
            return MarketEventsResult(clean, (), "nse-mcp", str(exc))


def _source_date(row: dict[str, Any]) -> date | None:
    """Read the provider timestamp rather than labelling stale data as today."""
    for field in ("date", "asOfDate", "lastUpdateDate", "timestamp", "lastUpdateTime"):
        value = row.get(field)
        if not value:
            continue
        try:
            return parse_nse_date(str(value))
        except ValueError:
            continue
    return None


def _first_present(row: dict[str, Any], *fields: str) -> Any:
    """Return the first non-empty provider value from equivalent field names."""
    for field in fields:
        value = row.get(field)
        if value is not None and value != "":
            return value
    return None


def report_to_dict(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: report_to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: report_to_dict(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [report_to_dict(item) for item in value]
    return value
