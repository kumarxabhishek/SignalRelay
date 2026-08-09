import pytest

from data_layer.symbols import normalize_nse_symbol, to_yfinance_ticker


def test_ticker_normalization_is_central_and_explicit() -> None:
    assert normalize_nse_symbol(" reliance.ns ") == "RELIANCE"
    assert to_yfinance_ticker("reliance") == "RELIANCE.NS"
    assert to_yfinance_ticker("Nifty 50") == "^NSEI"


def test_invalid_symbol_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_nse_symbol("RELIANCE; DROP")

