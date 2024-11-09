from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: bytes, sender: WebSocket):
        for connection in self.active_connections:
            if connection != sender:
                await connection.send_bytes(data)

manager = ConnectionManager()

@router.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            await manager.broadcast(data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)