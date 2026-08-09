"""Bounded fresh-data retry policy for the complete Phase 3 request path."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryOutcome(Generic[T]):
    value: T
    attempts: int
    retried: bool
    exhausted: bool


async def run_with_one_fresh_retry(run_attempt: Callable[[bool], Awaitable[tuple[T, bool]]]) -> RetryOutcome[T]:
    """Run once, then restart with fresh data at most once for a transient failure."""
    value, retryable_failure = await run_attempt(False)
    if not retryable_failure:
        return RetryOutcome(value, attempts=1, retried=False, exhausted=False)
    refreshed_value, retryable_failure = await run_attempt(True)
    return RetryOutcome(refreshed_value, attempts=2, retried=True, exhausted=retryable_failure)
