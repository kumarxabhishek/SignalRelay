import json

from fastapi.testclient import TestClient

from api import app as api_module
from server.errors import MarketDataUnavailableError, UnknownNseSymbolError


def test_signal_report_endpoint_uses_existing_backend(monkeypatch) -> None:
    async def fake_signal_report(symbol: str) -> str:
        assert symbol == "RELIANCE"
        return json.dumps({"phase": 2, "signals": [], "raw_evidence": {}})

    monkeypatch.setattr(api_module, "build_signal_report", fake_signal_report)
    response = TestClient(api_module.app).post("/v1/reports", json={"symbol": "RELIANCE"})
    assert response.status_code == 200
    assert response.json()["phase"] == 2


def test_explained_report_selection_and_api_key(monkeypatch) -> None:
    async def fake_explained_report(symbol: str) -> str:
        return json.dumps({"phase": 3, "reports": []})

    monkeypatch.setenv("SIGNALRELAY_API_TOKEN", "test-token")
    monkeypatch.setattr(api_module, "build_explained_report", fake_explained_report)
    client = TestClient(api_module.app)
    assert client.post("/v1/reports", json={"symbol": "TCS", "include_explanation": True}).status_code == 401
    response = client.post("/v1/reports", json={"symbol": "TCS", "include_explanation": True}, headers={"X-API-Key": "test-token"})
    assert response.status_code == 200
    assert response.json()["phase"] == 3


def test_report_input_is_validated() -> None:
    response = TestClient(api_module.app).post("/v1/reports", json={"symbol": "BAD SYMBOL"})
    assert response.status_code == 422


def test_unknown_but_well_formed_symbol_returns_404(monkeypatch) -> None:
    async def missing_symbol(symbol: str) -> str:
        raise UnknownNseSymbolError("No NSE-listed symbol was found for 'RELIANSE'. Check the ticker and try again.")

    monkeypatch.setattr(api_module, "build_signal_report", missing_symbol)
    response = TestClient(api_module.app).post("/v1/reports", json={"symbol": "RELIANSE"})
    assert response.status_code == 404
    assert "Check the ticker" in response.json()["detail"]


def test_temporary_market_data_failure_returns_503(monkeypatch) -> None:
    async def unavailable(symbol: str) -> str:
        raise MarketDataUnavailableError("The live quote source is currently unavailable. Try again shortly.")

    monkeypatch.setattr(api_module, "build_signal_report", unavailable)
    response = TestClient(api_module.app).post("/v1/reports", json={"symbol": "RELIANCE"})
    assert response.status_code == 503


def test_rate_limit_returns_retry_after(monkeypatch) -> None:
    monkeypatch.setenv("SIGNALRELAY_RATE_LIMIT", "1")
    api_module.rate_limiter._requests.clear()
    client = TestClient(api_module.app)
    assert client.get("/health").status_code == 200
    first = client.post("/v1/reports", json={"symbol": "BAD SYMBOL"})
    second = client.post("/v1/reports", json={"symbol": "BAD SYMBOL"})
    assert first.status_code == 422
    assert second.status_code == 429
    assert second.headers["retry-after"]


def test_ready_checks_live_report_path(monkeypatch) -> None:
    async def ready_report(symbol: str) -> str:
        assert symbol == "RELIANCE"
        return json.dumps({"phase": 2})

    monkeypatch.setattr(api_module, "build_signal_report", ready_report)
    response = TestClient(api_module.app).get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
