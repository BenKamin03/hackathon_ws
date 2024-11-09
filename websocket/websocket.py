from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.websockets import WebSocketState
import json
import asyncio
import os
import websockets
import ssl

router = APIRouter()
load_dotenv()

# Connection Manager for handling multiple WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: bytes, sender: WebSocket):
        for connection in self.active_connections:
            if connection != sender and connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_bytes(data)
                except Exception:
                    pass  # Suppress errors during broadcasting

manager = ConnectionManager()

async def deepgram_transcribe(deepgram_socket: websockets.WebSocketClientProtocol, websocket: WebSocket, data):
    """Receive transcriptions from Deepgram and send to the client WebSocket."""
    try:
        await deepgram_socket.send(data)
        response = await deepgram_socket.recv()
        response_data = json.loads(response)
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(response_data)
    except Exception:
        pass  # Suppress any errors to avoid printing task errors

@router.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for receiving audio data and sending it to Deepgram."""
    await manager.connect(websocket)
    
    # Create SSL context to ignore certificate verification (not recommended for production)
    ssl_context = ssl.SSLContext()
    ssl_context.verify_mode = ssl.CERT_NONE

    deepgram_socket = await websockets.connect(
        'wss://api.deepgram.com/v1/listen?smart_format=true',
        extra_headers={
            'Authorization': f'Token {os.getenv("DEEPGRAM_API_KEY")}'
        },
        ssl=ssl_context
    )

    try:
        while True:
            # Receive audio data from the client WebSocket
            data = await websocket.receive_bytes()

            # Run the transcription task without printing any errors
            asyncio.create_task(deepgram_transcribe(deepgram_socket, websocket, data))

            # Broadcast the data to other clients
            await manager.broadcast(data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await deepgram_socket.close()
    except Exception:
        pass  # Suppress other exceptions to avoid unwanted prints