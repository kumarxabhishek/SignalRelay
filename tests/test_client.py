import asyncio
import json
from types import SimpleNamespace

from data_layer.cache import AsyncTTLCache
from data_layer.client import NseDataClient, SubprocessNseTransport, VercelNseBridgeTransport


def response(payload: object) -> SimpleNamespace:
    return SimpleNamespace(isError=False, content=[SimpleNamespace(type="text", text=json.dumps(payload))])


class FakeTransport:
    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        await asyncio.sleep(0.01 if arguments.get("symbol") == "TCS" else 0)
        if arguments.get("symbol") == "FAIL":
            raise TimeoutError("simulated NSE-MCP timeout")
        if name == "get_quote":
            return response({"price": 100.0, "previousClose": 95.0, "volume": 1000})
        if name == "get_bulk_deals":
            return response([{"date": "10-Jul-2026", "clientName": "Fund A", "dealType": "BUY", "quantity": 10, "price": 99.5}])
        if name == "get_insider_trading":
            return response([{"acquirerName": "Director", "personCategory": "Promoter", "sharesAcquired": 5, "acquireFromDate": "2026-07-10", "acquireToDate": "2026-07-10", "intimationDate": "11-Jul-2026"}])
        if name == "get_fii_dii_activity":
            return response([{"date": "10-Jul-2026", "fiiNetValue": 4.5, "diiNetValue": -2.0}])
        if name == "get_nifty_indices":
            return response([{"name": "NIFTY 50", "date": "10-Jul-2026", "lastPrice": 24000.0, "percentChange": 0.5}])
        raise AssertionError(name)


async def test_normal_success_normalizes_types() -> None:
    client = NseDataClient(FakeTransport())
    quote, deals, insiders, flows = await asyncio.gather(client.get_quote("reliance"), client.get_bulk_deals("reliance"), client.get_insider_trades("reliance"), client.get_fii_dii_flows())
    assert quote.price == 100.0 and quote.pct_change == pytest_approx(5.2631578947)
    assert deals.deals[0].date.isoformat() == "2026-07-10"
    assert insiders.trades[0].intimation_date.isoformat() == "2026-07-11"
    assert flows.flows[0].dii_net_value == -2.0


async def test_quote_accepts_adapter_field_name_variants() -> None:
    class VariantQuoteTransport:
        async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
            assert name == "get_quote"
            return response({"lastPrice": "101.5", "previous_close": "100", "totalTradedVolume": "2500"})

    quote = await NseDataClient(VariantQuoteTransport()).get_quote("RELIANCE")
    assert (quote.price, quote.change, quote.pct_change, quote.volume) == (101.5, 1.5, 1.5, 2500)


async def test_failure_becomes_typed_result() -> None:
    result = await NseDataClient(FakeTransport()).get_quote("FAIL")
    assert result.error == "simulated NSE-MCP timeout"
    assert result.price is None


async def test_upstream_error_text_is_preserved_for_safe_classification() -> None:
    class ErrorTransport:
        async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
            return SimpleNamespace(isError=True, content=[SimpleNamespace(type="text", text="Error: Yahoo Finance failed for RELIANSE.NS: Cannot read properties of undefined (reading 'symbol')")])

    result = await NseDataClient(ErrorTransport()).get_quote("RELIANSE")
    assert "Yahoo Finance failed" in result.error


async def test_overlapping_requests_stay_correlated_to_their_symbols() -> None:
    client = NseDataClient(FakeTransport())
    reliance, tcs = await asyncio.gather(client.get_quote("RELIANCE"), client.get_quote("TCS"))
    assert (reliance.symbol, tcs.symbol) == ("RELIANCE", "TCS")


async def test_cache_coalesces_a_key_without_serializing_other_keys() -> None:
    cache: AsyncTTLCache[str] = AsyncTTLCache()
    calls: list[str] = []

    async def loader(name: str) -> str:
        calls.append(name)
        await asyncio.sleep(0.02)
        return name

    first, duplicate, independent = await asyncio.gather(
        cache.get_or_load("one", lambda: loader("one")),
        cache.get_or_load("one", lambda: loader("duplicate")),
        cache.get_or_load("two", lambda: loader("two")),
    )
    assert (first, duplicate, independent) == ("one", "one", "two")
    assert sorted(calls) == ["one", "two"]


async def test_index_snapshot_uses_provider_date() -> None:
    result = await NseDataClient(FakeTransport()).get_nifty_50_snapshot()
    assert result.index is not None
    assert result.index.as_of.isoformat() == "2026-07-10"


def test_vercel_bridge_is_used_only_when_configured(monkeypatch) -> None:
    monkeypatch.delenv("SIGNALRELAY_NSE_BRIDGE_URL", raising=False)
    assert isinstance(NseDataClient().transport, SubprocessNseTransport)
    monkeypatch.setenv("SIGNALRELAY_NSE_BRIDGE_URL", "https://signalrelay.example/api/nse-bridge")
    monkeypatch.setenv("SIGNALRELAY_NSE_BRIDGE_TOKEN", "bridge-secret")
    transport = NseDataClient().transport
    assert isinstance(transport, VercelNseBridgeTransport)
    assert transport.url == "https://signalrelay.example/api/nse-bridge"


def pytest_approx(value: float):
    import pytest
    return pytest.approx(value)
