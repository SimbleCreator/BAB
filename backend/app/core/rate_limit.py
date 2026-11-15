"""Simple in-process sliding-window rate limiter, keyed by client IP.

Per process only: fine for one container. Behind a proxy, run uvicorn with
--proxy-headers so request.client.host is the real client IP.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request

from app.core.errors import RateLimitError


class RateLimiter:
    def __init__(self, name: str, max_calls: int, window_seconds: int) -> None:
        self.name = name
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.max_calls:
                raise RateLimitError("Too many attempts. Wait a few minutes and try again.")
            hits.append(now)
            if len(self._hits) > 10_000:  # drop idle keys so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    async def __call__(self, request: Request) -> None:
        self.hit(request.client.host if request.client else "unknown")


login_limiter = RateLimiter("login", max_calls=10, window_seconds=5 * 60)
register_limiter = RateLimiter("register", max_calls=5, window_seconds=60 * 60)
