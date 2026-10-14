from __future__ import annotations

import asyncio
import time


class MinIntervalLimiter:
    """Spaces calls at least `interval` seconds apart, across every caller in the process.

    For APIs whose usage policy sets a request rate per client (crates.io: one
    per second). Concurrent sourcing runs share one instance per host.
    """

    def __init__(self, interval: float):
        self._interval = interval
        self._lock = asyncio.Lock()
        self._last = float("-inf")

    async def wait(self) -> None:
        async with self._lock:
            delay = self._last + self._interval - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._last = time.monotonic()
