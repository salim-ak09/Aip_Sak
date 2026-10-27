from __future__ import annotations

import asyncio
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class ConnectionManager:
    """Manages active WebSocket connections, broadcasting, and resume playback."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._history: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("ws_client_connected", count=len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("ws_client_disconnected", count=len(self.active_connections))

    async def record_and_broadcast(self, event: dict[str, Any]) -> None:
        async with self._lock:
            self._history.append(event)
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_json(event)
            except Exception:
                await self.disconnect(connection)

    async def replay_since(
        self, websocket: WebSocket, since_event_id: str | None = None
    ) -> None:
        """Sends missed events to a newly connected or reconnected client."""
        async with self._lock:
            events = list(self._history)

        if not since_event_id:
            for ev in events:
                await websocket.send_json(ev)
            return

        idx = -1
        for i, ev in enumerate(events):
            if str(ev.get("id")) == str(since_event_id):
                idx = i
                break

        if idx != -1:
            # Replay all events that occurred after since_event_id
            for ev in events[idx + 1:]:
                await websocket.send_json(ev)
        else:
            # Fallback to all if event_id not found in memory buffer
            for ev in events:
                await websocket.send_json(ev)


manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket, since: str | None = None
) -> None:
    """WebSocket stream handler supporting since=<event_id> reconnect recovery."""
    await manager.connect(websocket)
    try:
        if since:
            await manager.replay_since(websocket, since)

        while True:
            # Receive client ping or control signals
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.warning("ws_error", error=str(e))
        await manager.disconnect(websocket)
