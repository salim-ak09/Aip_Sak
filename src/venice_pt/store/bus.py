from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator

from venice_pt.contracts.events import Event


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[Event]]] = defaultdict(set)
        self._global_subscribers: set[asyncio.Queue[Event]] = set()
        self._lock = asyncio.Lock()

    async def publish(self, event: Event) -> None:
        """Publishes an event to matching engagement subscribers and global listeners."""
        async with self._lock:
            target_queues = list(self._subscribers[event.engagement_id]) + list(
                self._global_subscribers
            )

        for q in target_queues:
            await q.put(event)

    async def subscribe(self, engagement_id: str | None = None) -> AsyncIterator[Event]:
        """Subscribes to an async stream of events for an engagement or globally."""
        queue: asyncio.Queue[Event] = asyncio.Queue()
        async with self._lock:
            if engagement_id:
                self._subscribers[engagement_id].add(queue)
            else:
                self._global_subscribers.add(queue)

        try:
            while True:
                event = await queue.get()
                yield event
                queue.task_done()
        finally:
            async with self._lock:
                if engagement_id:
                    self._subscribers[engagement_id].discard(queue)
                else:
                    self._global_subscribers.discard(queue)
