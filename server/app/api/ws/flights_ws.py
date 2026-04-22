import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.models.schemas import WsEvent
from app.state import broadcast_manager, flight_store

router = APIRouter(prefix="/api/v1", tags=["ws"])


@router.websocket("/ws/flights")
async def flights_socket(websocket: WebSocket) -> None:
    """Push flight snapshots to web clients.

    On connect, the client receives an immediate snapshot.  Subsequent updates
    are pushed by the pipeline broadcast whenever new realtime data arrives.
    A heartbeat ping is sent every WS_HEARTBEAT_SECONDS to keep the connection
    alive and let clients detect stale connections.
    """

    await broadcast_manager.connect(websocket)
    try:
        # Send initial snapshot so the client has data immediately.
        flights = await flight_store.list_flights()
        initial = WsEvent(
            event="snapshot",
            ts=datetime.now(timezone.utc),
            data=[f.model_dump(mode="json") for f in flights],
        )
        await websocket.send_json(initial.model_dump(mode="json"))

        # Keep connection alive with periodic heartbeats.
        while True:
            await asyncio.sleep(settings.ws_heartbeat_seconds)
            ping = WsEvent(event="ping", ts=datetime.now(timezone.utc), data=None)
            await websocket.send_json(ping.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    finally:
        await broadcast_manager.disconnect(websocket)
