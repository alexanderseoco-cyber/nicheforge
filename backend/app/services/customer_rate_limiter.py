"""Centralized per-customer provider invocation throttling."""
from __future__ import annotations

import asyncio
import time


class CustomerRateLimiter:
    """Serialize calls per customer while allowing independent customers."""

    def __init__(self, *, requests_per_second: float = 1.0, enabled: bool = False,
                 clock=time.monotonic, sleep=asyncio.sleep):
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.interval = 1.0 / requests_per_second
        self.enabled = enabled
        self._clock = clock
        self._sleep = sleep
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_started: dict[str, float] = {}

    async def acquire(self, customer_id: str | None) -> None:
        if not self.enabled or not customer_id:
            return
        lock = self._locks.setdefault(customer_id, asyncio.Lock())
        async with lock:
            now = self._clock()
            wait_for = self.interval - (now - self._last_started.get(customer_id, now - self.interval))
            if wait_for > 0:
                await self._sleep(wait_for)
            self._last_started[customer_id] = self._clock()
