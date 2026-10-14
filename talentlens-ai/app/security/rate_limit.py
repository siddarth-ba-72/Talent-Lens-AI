from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Lock

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.errors import RateLimitedError


logger = logging.getLogger(__name__)

_PRUNE_THRESHOLD = 10_000


@dataclass
class _Window:
    count: int
    started_at: float


class AttemptLimiter:
    """Fixed-window attempt counter keyed by client address (in-memory, per process)."""

    def __init__(self) -> None:
        self._windows: dict[str, _Window] = {}
        self._lock = Lock()

    def is_limited(self, key: str, max_attempts: int, window_seconds: float) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._windows) > _PRUNE_THRESHOLD:
                self._windows = {
                    k: w for k, w in self._windows.items() if now - w.started_at <= window_seconds
                }
            window = self._windows.get(key)
            if window is None or now - window.started_at > window_seconds:
                window = _Window(count=0, started_at=now)
                self._windows[key] = window
            window.count += 1
            return window.count > max_attempts

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()


auth_limiter = AttemptLimiter()


def _client_ip(request: Request) -> str:
    # Deliberately not read from X-Forwarded-For here: the header is caller-supplied.
    # Behind a proxy, uvicorn's --forwarded-allow-ips decides which hops to trust
    # and rewrites request.client accordingly.
    return request.client.host if request.client else "unknown"


async def limit_auth_attempts(request: Request, settings: Settings = Depends(get_settings)) -> None:
    client_ip = _client_ip(request)
    if auth_limiter.is_limited(client_ip, settings.rate_limit_max_attempts, settings.rate_limit_window_seconds):
        logger.warning("Rate limit exceeded for IP: %s", client_ip)
        raise RateLimitedError(
            "Too many attempts. Please try again later.",
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )
