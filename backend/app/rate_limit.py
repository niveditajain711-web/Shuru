import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """In-memory sliding-window limiter: at most `limit` hits per `window_seconds` per key.

    Fine for one process (the demo runs a single container). Behind a reverse proxy the key is the
    proxy's address unless the proxy forwards the client IP; see architecture section 10.
    """

    def __init__(self, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True
