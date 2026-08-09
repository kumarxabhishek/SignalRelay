"""Public error categories shared by MCP and HTTP entry points."""


class UnknownNseSymbolError(ValueError):
    """The supplied ticker is syntactically valid but is not an NSE quote."""


class MarketDataUnavailableError(RuntimeError):
    """A required upstream market-data request failed temporarily."""
