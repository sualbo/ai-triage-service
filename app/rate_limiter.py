from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

from app.config import settings


class RateLimitExceeded(Exception):
    """Raised when a client exceeds the configured requests-per-minute limit."""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    """Simple per-client sliding-window rate limiter.

    This is enough for a single-process MVP. For production, replace it with Redis
    or another shared store.
    """

    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self.window_seconds = 60
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_id: str) -> RateLimitDecision:
        now = time.monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            events = self._events[client_id]
            while events and events[0] < window_start:
                events.popleft()

            if len(events) >= self.limit_per_minute:
                retry_after = max(1, int(self.window_seconds - (now - events[0])))
                return RateLimitDecision(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            events.append(now)
            remaining = max(0, self.limit_per_minute - len(events))
            return RateLimitDecision(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=0,
            )


rate_limiter = InMemoryRateLimiter(settings.requests_per_minute)
