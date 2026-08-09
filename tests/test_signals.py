from datetime import date, timedelta

from data_layer.models import (
    BulkDeal, BulkDealsResult, FiiDiiFlow, FiiDiiFlowsResult, IndexSnapshot,
    InsiderTrade, InsiderTradesResult,
)
from signals.models import DeliveryObservation
from signals.rules import (
    detect_delivery_spike_with_bulk_deal,
    detect_fii_index_divergence,
    detect_insider_bulk_divergence,
)


DAY = date(2026, 7, 10)


def deal(day: date = DAY) -> BulkDealsResult:
    return BulkDealsResult("RELIANCE", (BulkDeal(day, "RELIANCE", "Fund A", "BUY", 10, 100.0),), "nse-mcp")


def test_insider_bulk_divergence_fires_on_disclosed_sale_near_buy() -> None:
    insiders = InsiderTradesResult("RELIANCE", (InsiderTrade("RELIANCE", "Director", "Promoter", 50, "Market Sale", DAY, DAY, DAY),), "nse-mcp")
    signal = detect_insider_bulk_divergence(insiders, deal())
    assert signal is not None and signal.signal_type == "insider_bulk_divergence"


def test_insider_bulk_divergence_does_not_treat_insider_buy_as_sale() -> None:
    insiders = InsiderTradesResult("RELIANCE", (InsiderTrade("RELIANCE", "Director", "Promoter", 50, "Market Purchase", DAY, DAY, DAY),), "nse-mcp")
    assert detect_insider_bulk_divergence(insiders, deal()) is None


def test_delivery_spike_requires_history_and_same_day_bulk_deal() -> None:
    history = tuple(DeliveryObservation(DAY - timedelta(days=30 - offset), 40.0) for offset in range(30)) + (DeliveryObservation(DAY, 70.0),)
    signal = detect_delivery_spike_with_bulk_deal(history, deal())
    assert signal is not None and signal.signal_type == "delivery_spike_with_bulk_deal"
    assert detect_delivery_spike_with_bulk_deal(history[:30], deal()) is None


def test_fii_index_divergence_requires_exact_same_day_opposition() -> None:
    flows = FiiDiiFlowsResult((FiiDiiFlow(DAY, -50.0, 20.0),), "nse-mcp")
    index = IndexSnapshot("NIFTY 50", DAY, 24000.0, 1.0)
    signal = detect_fii_index_divergence(flows, index)
    assert signal is not None and signal.signal_type == "fii_index_divergence"
    assert detect_fii_index_divergence(flows, IndexSnapshot("NIFTY 50", DAY + timedelta(days=1), 24000.0, 1.0)) is None
