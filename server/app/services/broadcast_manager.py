"""WebSocket broadcast manager.

Maintains a registry of active WebSocket connections and fans out events to all
connected clients. Dead connections are silently removed during the next broadcast.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

from app.models.schemas import WsEvent

logger = logging.getLogger(__name__)


class BroadcastManager:
    """Thread-safe fan-out broadcaster for WebSocket connections."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: set[WebSocket] = set()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a new WebSocket client."""
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.debug("WS client connected (total=%d)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        """Deregister a WebSocket client."""
        async with self._lock:
            self._connections.discard(ws)
        logger.debug("WS client disconnected (total=%d)", len(self._connections))

    async def broadcast(self, event: WsEvent) -> None:
        """Serialize *event* and push to all registered clients.

        Connections that raise during send are silently removed.
        """
        async with self._lock:
            if not self._connections:
                return
            payload = event.model_dump(mode="json")
            dead: set[WebSocket] = set()
            for ws in self._connections:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.add(ws)
            self._connections -= dead
        if dead:
            logger.debug("Removed %d dead WS connections", len(dead))
