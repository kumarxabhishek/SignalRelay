from data_layer.models import QuoteResult
from server.app import _quote_source_status


def test_quote_source_status_marks_missing_core_fields_as_partial() -> None:
    quote = QuoteResult("RELIANCE", None, None, None, 9_885_638, "nse-mcp")

    assert _quote_source_status(quote) == {
        "available": False,
        "status": "partial",
        "missing_fields": ("last_price", "change"),
        "error": None,
    }


def test_quote_source_status_marks_complete_quote_as_available() -> None:
    quote = QuoteResult("RELIANCE", 100.0, 2.0, 2.04, 10_000, "nse-mcp")

    assert _quote_source_status(quote)["status"] == "available"
