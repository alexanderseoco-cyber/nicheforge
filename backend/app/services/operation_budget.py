"""Provider-operation capacity guard for actual Google RPC attempts."""
from __future__ import annotations

import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone


class OperationBudgetExceeded(RuntimeError):
    """The configured provider operation budget cannot admit this attempt."""


class OperationBudgetGuard:
    """Process-local atomic rolling-24-hour operation guard.

    A missing limit intentionally means ``unknown/unverified`` and never blocks
    execution. The counter is per customer over the last 24 hours, and counts attempts,
    not keywords or planned combinations.
    """

    def __init__(self, daily_limit: int | None = None):
        if daily_limit is not None and daily_limit < 0:
            raise ValueError("daily operation budget must be non-negative")
        self.daily_limit = daily_limit
        self._attempts: defaultdict[str, deque[tuple[datetime, int]]] = defaultdict(deque)
        self._lock = threading.Lock()

    @property
    def status(self) -> str:
        return "UNKNOWN_UNVERIFIED" if self.daily_limit is None else "CONFIGURED"

    def reserve_attempt(self, customer_id: str | None, operations: int = 1) -> None:
        if operations < 0:
            raise ValueError("operations must not be negative")
        if self.daily_limit is None or operations == 0:
            return
        key = customer_id or "unknown"
        now = datetime.now(timezone.utc)
        with self._lock:
            attempts = self._attempts[key]
            cutoff = now - timedelta(hours=24)
            while attempts and attempts[0][0] <= cutoff:
                attempts.popleft()
            if sum(count for _, count in attempts) + operations > self.daily_limit:
                raise OperationBudgetExceeded("Google Ads operation budget exceeded")
            attempts.append((now, operations))

    def used(self, customer_id: str | None) -> int:
        key = customer_id or "unknown"
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0][0] <= cutoff:
                attempts.popleft()
            return sum(count for _, count in attempts)
