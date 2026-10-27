from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Per-host token bucket rate limiter."""

    def __init__(self, default_rate: float = 10.0, default_delay_s: float = 0.0) -> None:
        self.default_rate = default_rate
        self.default_delay_s = default_delay_s
        self._tokens: dict[str, float] = {}
        self._last_update: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, host: str, rate: float | None = None) -> None:
        r = rate if rate is not None else self.default_rate
        if r <= 0:
            return

        async with self._lock:
            now = time.monotonic()
            last = self._last_update.get(host, now)
            tokens = self._tokens.get(host, r)

            # Refill tokens
            elapsed = now - last
            tokens = min(r, tokens + elapsed * r)

            if tokens < 1.0:
                wait_time = (1.0 - tokens) / r
                await asyncio.sleep(wait_time)
                now = time.monotonic()
                tokens = 0.0
            else:
                tokens -= 1.0

            self._tokens[host] = tokens
            self._last_update[host] = now
            if self.default_delay_s > 0:
                await asyncio.sleep(self.default_delay_s)
