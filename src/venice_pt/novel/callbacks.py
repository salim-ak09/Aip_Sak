from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class CallbackEvent(BaseModel):
    nonce: str
    source_ip: str
    protocol: str  # "HTTP" or "DNS"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_data: str = ""


class CallbackListener:
    """In-process out-of-band interaction tracker for correlating blind SSRF / OOB probes."""

    def __init__(self) -> None:
        self.received_callbacks: dict[str, list[CallbackEvent]] = {}
        self._lock = asyncio.Lock()

    async def register_interaction(
        self, nonce: str, source_ip: str, protocol: str = "HTTP", raw_data: str = ""
    ) -> CallbackEvent:
        event = CallbackEvent(
            nonce=nonce,
            source_ip=source_ip,
            protocol=protocol,
            raw_data=raw_data,
        )
        async with self._lock:
            self.received_callbacks.setdefault(nonce, []).append(event)
        logger.info("oob_callback_received", nonce=nonce, ip=source_ip, proto=protocol)
        return event

    async def check_nonce(self, nonce: str) -> list[CallbackEvent]:
        async with self._lock:
            return list(self.received_callbacks.get(nonce, []))

    async def wait_for_callback(self, nonce: str, timeout_seconds: float = 2.0) -> bool:
        """Polls for callback event for given nonce up to timeout."""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            events = await self.check_nonce(nonce)
            if events:
                return True
            await asyncio.sleep(0.1)
        return False


global_callback_listener = CallbackListener()
