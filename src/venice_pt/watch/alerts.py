from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger()


class AlertDispatcher:
    """Dispatches notifications with deduplication suppression windows."""

    def __init__(self, suppression_seconds: float = 300.0) -> None:
        self.suppression_seconds = suppression_seconds
        self._recent_alerts: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def should_send_alert(self, alert_key: str) -> bool:
        """Determines if alert should be emitted or suppressed as duplicate."""
        now = asyncio.get_event_loop().time()
        async with self._lock:
            last_sent = self._recent_alerts.get(alert_key)
            if last_sent is not None and (now - last_sent) < self.suppression_seconds:
                logger.info("alert_suppressed_duplicate", key=alert_key)
                return False

            self._recent_alerts[alert_key] = now
            return True

    async def dispatch(self, title: str, message: str, alert_key: str) -> bool:
        """Dispatches alert if not suppressed."""
        if not await self.should_send_alert(alert_key):
            return False

        logger.info(
            "alert_dispatched",
            title=title,
            message=message,
            timestamp=datetime.now(UTC).isoformat(),
        )
        return True


global_alert_dispatcher = AlertDispatcher()
