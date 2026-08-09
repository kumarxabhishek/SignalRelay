"""Classify disclosed corporate events; this adds context, not a trade signal."""
from __future__ import annotations

from data_layer.models import MarketEvent

_EVENT_KEYWORDS = {
    "earnings": ("financial results", "quarterly results", "earnings", "result"),
    "dividend": ("dividend",),
    "stock_split": ("split", "sub-division"),
    "bonus_issue": ("bonus",),
    "rights_issue": ("rights issue",),
    "merger_or_acquisition": ("merger", "amalgamation", "acquisition", "scheme of arrangement"),
}


def classify_event(description: str) -> str | None:
    text = description.lower()
    for event_type, keywords in _EVENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return event_type
    return None


def detected_events(events: tuple[MarketEvent, ...]) -> tuple[MarketEvent, ...]:
    """Keep only recognized event categories and never infer beyond disclosure text."""
    return tuple(event for event in events if event.event_type != "other")
