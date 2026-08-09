"""Pure rule functions. They are intentionally independent from MCP and LLMs."""
from __future__ import annotations

from datetime import date

from data_layer.models import BulkDealsResult, FiiDiiFlowsResult, IndexSnapshot, InsiderTradesResult
from .models import DeliveryObservation, Signal


def _is_sale(mode: str, shares: int | None) -> bool:
    return (shares is not None and shares < 0) or any(word in mode.lower() for word in ("sale", "sell", "disposal"))


def detect_insider_bulk_divergence(
    insiders: InsiderTradesResult,
    bulk_deals: BulkDealsResult,
    *,
    window_days: int = 5,
) -> Signal | None:
    """Flag disclosed insider selling paired with a reported bulk-deal buy nearby.

    The bulk counterparty is not labelled "institutional" unless a future
    verified classification source is added; this is evidence, not attribution.
    """
    sales = [trade for trade in insiders.trades if _is_sale(trade.mode_of_acquisition, trade.shares_acquired)]
    buys = [deal for deal in bulk_deals.deals if deal.deal_type == "BUY" and deal.date]
    for sale in sales:
        sale_date = sale.acquisition_to_date or sale.intimation_date or sale.acquisition_from_date
        if sale_date is None:
            continue
        for buy in buys:
            if abs((buy.date - sale_date).days) <= window_days:
                return Signal(
                    "insider_bulk_divergence", 0.55,
                    "A disclosed insider sale and a reported bulk-deal buy occurred close together; counterparty classification is not verified.",
                    (f"Insider {sale.acquirer_name or 'disclosure'} reported a sale on {sale_date.isoformat()}.", f"Bulk-deal buyer {buy.client_name or 'not named'} bought {buy.quantity or 0} shares on {buy.date.isoformat()}."),
                    (sale_date, buy.date),
                )
    return None


def detect_delivery_spike_with_bulk_deal(
    delivery_history: tuple[DeliveryObservation, ...], bulk_deals: BulkDealsResult, *, multiplier: float = 1.5,
) -> Signal | None:
    """Flag today's delivery percentage above 1.5× its preceding 30-observation mean."""
    if len(delivery_history) < 31:
        return None
    latest, prior = delivery_history[-1], delivery_history[-31:-1]
    average = sum(item.delivery_pct for item in prior) / len(prior)
    has_same_day_deal = any(deal.date == latest.date for deal in bulk_deals.deals)
    if average > 0 and latest.delivery_pct > multiplier * average and has_same_day_deal:
        return Signal(
            "delivery_spike_with_bulk_deal", 0.6,
            "This is a descriptive volume-delivery pattern, not a price forecast.",
            (f"Delivery percentage was {latest.delivery_pct:.2f}% on {latest.date.isoformat()}.", f"The preceding 30-observation average was {average:.2f}%.", "A bulk deal was reported on the same date."),
            (latest.date,),
        )
    return None


def detect_fii_index_divergence(flows: FiiDiiFlowsResult, index: IndexSnapshot | None) -> Signal | None:
    """Compare the latest FII net flow with same-day Nifty price direction."""
    if index is None or index.pct_change is None:
        return None
    same_day = next((flow for flow in flows.flows if flow.date == index.as_of and flow.fii_net_value is not None), None)
    if same_day is None or same_day.fii_net_value == 0 or index.pct_change == 0:
        return None
    opposed = (same_day.fii_net_value < 0 < index.pct_change) or (same_day.fii_net_value > 0 > index.pct_change)
    if not opposed:
        return None
    direction = "selling" if same_day.fii_net_value < 0 else "buying"
    return Signal(
        "fii_index_divergence", 0.5,
        "This is a same-day market-flow contrast, not proof of stock- or sector-specific causation.",
        (f"FII net {direction} was {same_day.fii_net_value:.2f} on {same_day.date.isoformat()}.", f"{index.name} changed {index.pct_change:.2f}% on the same date."),
        (same_day.date,),
    )
