"""Small, browser-facing API around the existing SignalRelay report builders."""
from __future__ import annotations

import json
import logging
import os
import secrets
import sys
import time
from collections import defaultdict, deque
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from server.app import build_explained_report, build_signal_report
from server.errors import MarketDataUnavailableError, UnknownNseSymbolError

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)


def _allowed_origins() -> list[str]:
    configured = os.environ.get("SIGNALRELAY_ALLOWED_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://localhost:5173"]


class ReportRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=25, pattern=r"^[A-Za-z0-9&._-]+$")
    include_explanation: bool = False


app = FastAPI(title="SignalRelay dashboard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


class InMemoryRateLimiter:
    """Small deployment-safe default; use a shared gateway limiter at scale."""
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allowed(self, client: str) -> tuple[bool, int]:
        limit = _positive_int_env("SIGNALRELAY_RATE_LIMIT", 60, allow_zero=True)
        window = _positive_int_env("SIGNALRELAY_RATE_WINDOW_SECONDS", 60)
        if limit <= 0:
            return True, 0
        now = time.monotonic()
        entries = self._requests[client]
        while entries and entries[0] <= now - window:
            entries.popleft()
        if not entries:
            self._requests.pop(client, None)
            entries = self._requests[client]
        if len(entries) >= limit:
            return False, max(1, int(window - (now - entries[0])))
        entries.append(now)
        return True, 0


rate_limiter = InMemoryRateLimiter()


def _positive_int_env(name: str, default: int, *, allow_zero: bool = False) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        logger.warning("Ignoring invalid %s value", name)
        return default
    minimum = 0 if allow_zero else 1
    if value < minimum:
        logger.warning("Ignoring out-of-range %s value", name)
        return default
    return value


@app.middleware("http")
async def limit_requests(request: Request, call_next):
    if request.url.path in {"/health", "/ready"}:
        return await call_next(request)
    client = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.allowed(client)
    if not allowed:
        return JSONResponse(status_code=429, content={"detail": "Too many requests; retry shortly."}, headers={"Retry-After": str(retry_after)})
    started_at = time.perf_counter()
    response = await call_next(request)
    logger.info(json.dumps({
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
    }))
    return response


def _check_api_key(x_api_key: str | None) -> None:
    """Local development is keyless; deployment may require an Edge Function key."""
    configured = [
        token.strip()
        for token in (
            os.environ.get("SIGNALRELAY_API_TOKEN", "") + "," +
            os.environ.get("SIGNALRELAY_ADDITIONAL_API_TOKENS", "")
        ).split(",")
        if token.strip()
    ]
    if configured and not any(x_api_key is not None and secrets.compare_digest(x_api_key, token) for token in configured):
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "claude_explanations_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@app.get("/ready")
async def ready() -> dict[str, object]:
    """Check the live quote path, including Node, NSE-MCP, and its upstream."""
    try:
        serialized = await build_signal_report(os.environ.get("SIGNALRELAY_READINESS_SYMBOL", "RELIANCE"))
        json.loads(serialized)
    except (MarketDataUnavailableError, UnknownNseSymbolError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Market-data dependency is not ready") from exc
    except Exception as exc:
        logger.exception("Readiness check failed")
        raise HTTPException(status_code=503, detail="Market-data dependency is not ready") from exc
    return {"status": "ready"}


@app.post("/v1/reports")
async def create_report(request: ReportRequest, x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    """Return a deterministic report, optionally including a verified explanation."""
    _check_api_key(x_api_key)
    try:
        serialized = await (build_explained_report(request.symbol) if request.include_explanation else build_signal_report(request.symbol))
        return json.loads(serialized)
    except UnknownNseSymbolError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MarketDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        logger.exception("Backend report serialization failed")
        raise HTTPException(status_code=500, detail="Report serialization failed") from exc
    except Exception as exc:
        logger.exception("Report generation failed for symbol %s", request.symbol)
        raise HTTPException(status_code=502, detail="Market-data report is currently unavailable") from exc


def run() -> None:
    host = os.environ.get("SIGNALRELAY_HOST", "127.0.0.1")
    port = int(os.environ.get("SIGNALRELAY_PORT", "8000"))
    uvicorn.run("api.app:app", host=host, port=port)
