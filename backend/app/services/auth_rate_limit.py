from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock

class AuthAttemptLimiter:
    def __init__(self, maximum: int = 10, window_seconds: int = 900):
        self.maximum = maximum; self.window = timedelta(seconds=window_seconds); self._events = defaultdict(deque); self._lock = Lock()
    def allow(self, key: str) -> bool:
        now = datetime.utcnow()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] > self.window: events.popleft()
            if len(events) >= self.maximum: return False
            events.append(now); return True
