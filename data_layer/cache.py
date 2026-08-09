"""Small concurrency-safe TTL cache for upstream MCP responses."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class _Entry(Generic[T]):
    expires_at: float
    value: T


class AsyncTTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._values: dict[str, _Entry[T]] = {}
        self._inflight: dict[str, asyncio.Task[T]] = {}
        self._lock = asyncio.Lock()

    async def get_or_load(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            cached = self._values.get(key)
            if cached and cached.expires_at > time.monotonic():
                return cached.value
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(self._load_and_cache(key, loader))
                self._inflight[key] = task
        # Do not hold the global lock while waiting on a network call. Shielding
        # also prevents one disconnected request from cancelling shared work.
        return await asyncio.shield(task)

    async def _load_and_cache(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        try:
            value = await loader()
            async with self._lock:
                self._values[key] = _Entry(time.monotonic() + self._ttl_seconds, value)
            return value
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    async def clear(self) -> None:
        """Force the next request to obtain fresh upstream data."""
        async with self._lock:
            self._values.clear()
