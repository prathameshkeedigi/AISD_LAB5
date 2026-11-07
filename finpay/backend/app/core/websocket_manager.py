from typing import Dict, List, Any
import json
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Store active connections by user_id (or "admin")
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.broadcast_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: str = "anonymous"):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        self.broadcast_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str = "anonymous"):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        if websocket in self.broadcast_connections:
            self.broadcast_connections.remove(websocket)

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        if client_id in self.active_connections:
            dead_sockets = []
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_sockets.append(connection)
            for s in dead_sockets:
                self.disconnect(s, client_id)

    async def broadcast(self, message: Dict[str, Any]):
        dead_sockets = []
        for connection in list(self.broadcast_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_sockets.append(connection)
        for s in dead_sockets:
            if s in self.broadcast_connections:
                self.broadcast_connections.remove(s)

manager = ConnectionManager()
