import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.schemas import WsEvent
from app.state import flight_store

router = APIRouter(prefix="/api/v1", tags=["ws"])


@router.websocket("/ws/flights")
async def flights_socket(websocket: WebSocket) -> None:
    """Push periodic flight snapshots to web clients.

    TODO: Replace polling push with event-driven broadcast for better scalability.
    """

    await websocket.accept()
    try:
        while True:
            flights = await flight_store.list_flights()
            payload = WsEvent(
                event="snapshot",
                ts=datetime.now(timezone.utc),
                data=[f.model_dump(mode="json") for f in flights],
            )
            await websocket.send_json(payload.model_dump(mode="json"))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
