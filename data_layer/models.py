"""Normalized typed records; raw provider strings never leave this module."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

Source = Literal["nse-mcp", "unavailable"]


def parse_nse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip().split(" ", maxsplit=1)[0]
    for pattern in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported NSE date format: {value!r}")


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def as_int(value: Any) -> int | None:
    number = as_float(value)
    return int(number) if number is not None else None


@dataclass(frozen=True)
class QuoteResult:
    symbol: str
    price: float | None
    change: float | None
    pct_change: float | None
    volume: int | None
    source: Source
    is_stale: bool = False
    error: str | None = None


@dataclass(frozen=True)
class BulkDeal:
    date: date | None
    symbol: str
    client_name: str
    deal_type: Literal["BUY", "SELL"]
    quantity: int | None
    price: float | None
    source: Source = "nse-mcp"


@dataclass(frozen=True)
class BulkDealsResult:
    symbol: str
    deals: tuple[BulkDeal, ...]
    source: Source
    error: str | None = None


@dataclass(frozen=True)
class InsiderTrade:
    symbol: str
    acquirer_name: str
    person_category: str
    shares_acquired: int | None
    mode_of_acquisition: str
    acquisition_from_date: date | None
    acquisition_to_date: date | None
    intimation_date: date | None
    source: Source = "nse-mcp"


@dataclass(frozen=True)
class InsiderTradesResult:
    symbol: str
    trades: tuple[InsiderTrade, ...]
    source: Source
    error: str | None = None


@dataclass(frozen=True)
class FiiDiiFlow:
    date: date
    fii_net_value: float | None
    dii_net_value: float | None
    source: Source = "nse-mcp"


@dataclass(frozen=True)
class FiiDiiFlowsResult:
    flows: tuple[FiiDiiFlow, ...]
    source: Source
    error: str | None = None


@dataclass(frozen=True)
class DeliveryHistoryResult:
    symbol: str
    records: tuple[object, ...]
    source: Source
    error: str | None = None


@dataclass(frozen=True)
class IndexSnapshot:
    name: str
    as_of: date
    last_price: float | None
    pct_change: float | None
    source: Source = "nse-mcp"


@dataclass(frozen=True)
class IndexSnapshotResult:
    index: IndexSnapshot | None
    source: Source
    error: str | None = None


@dataclass(frozen=True)
class MarketEvent:
    event_type: str
    event_date: date | None
    description: str
    source: str


@dataclass(frozen=True)
class MarketEventsResult:
    symbol: str
    events: tuple[MarketEvent, ...]
    source: Source
    error: str | None = None
