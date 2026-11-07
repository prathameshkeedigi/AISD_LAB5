from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from finpay.backend.app.core.websocket_manager import manager

router = APIRouter(tags=["Real-time WebSockets"])

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive & receive client heartbeats/pings
            data = await websocket.receive_text()
            # Send immediate acknowledgement pong
            await websocket.send_json({"event": "PONG", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception:
        manager.disconnect(websocket, client_id)
