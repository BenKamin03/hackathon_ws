from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List
from fastapi.responses import HTMLResponse

app = FastAPI()

# Configure CORS for HTTP endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_transcription(self, data: dict):
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

# Add a basic HTTP endpoint for testing
@app.get("/")
async def get():
    return {"message": "WebSocket server is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Handle the WebSocket connection request
    try:
        await manager.connect(websocket)
        print("A user connected")
        
        while True:
            data = await websocket.receive_text()
            print("Message received:", data)
            await manager.broadcast(f"Server received: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("A user disconnected")
    except Exception as e:
        print(f"Error: {e}")
        if websocket in manager.active_connections:
            manager.disconnect(websocket)

@app.websocket("/ws/transcription")
async def transcription_endpoint(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        
        while True:
            data = await websocket.receive_json()
            print("Transcription received:", data)
            await manager.broadcast_transcription(data)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("A user disconnected")
    except Exception as e:
        print(f"Error: {e}")
        if websocket in manager.active_connections:
            manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        # Enable WebSocket protocol
        ws_ping_interval=None,
        ws_ping_timeout=None
    )