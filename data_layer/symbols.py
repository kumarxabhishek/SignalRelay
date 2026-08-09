"""One place for all provider-specific ticker transformations."""
from __future__ import annotations

import re

_SYMBOL = re.compile(r"^[A-Z0-9&._-]{1,25}$")


def normalize_nse_symbol(symbol: str) -> str:
    """Return the bare NSE symbol accepted by NSE-MCP."""
    normalized = symbol.strip().upper()
    if normalized.endswith(".NS"):
        normalized = normalized[:-3]
    if not normalized or not _SYMBOL.fullmatch(normalized):
        raise ValueError(f"Invalid NSE symbol: {symbol!r}")
    return normalized


def to_yfinance_ticker(symbol: str) -> str:
    """Return yfinance's NSE ticker form; NIFTY 50 is a special Yahoo symbol."""
    if symbol.strip().upper() in {"NIFTY", "NIFTY50", "NIFTY 50", "^NSEI"}:
        return "^NSEI"
    return f"{normalize_nse_symbol(symbol)}.NS"

