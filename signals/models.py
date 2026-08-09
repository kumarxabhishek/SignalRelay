from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

SignalType = Literal[
    "insider_bulk_divergence",
    "delivery_spike_with_bulk_deal",
    "fii_index_divergence",
]


@dataclass(frozen=True)
class DeliveryObservation:
    date: date
    delivery_pct: float


@dataclass(frozen=True)
class Signal:
    signal_type: SignalType
    confidence: float
    confidence_note: str
    facts: tuple[str, ...]
    source_dates: tuple[date, ...]

