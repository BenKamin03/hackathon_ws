from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketState
from dotenv import load_dotenv
import json
import asyncio
import os
import websockets
import ssl
from ssl import SSLCertVerificationError

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
        self.active_connections.remove(websocket)

    async def broadcast(self, data: bytes, sender: WebSocket):
        for connection in self.active_connections:
            if connection != sender:
                await connection.send_bytes(data)

manager = ConnectionManager()

async def deepgram_transcribe(deepgram_socket: websockets.WebSocketClientProtocol, websocket: WebSocket):
    response = await deepgram_socket.recv()
    response_data = json.loads(response)
    await websocket.send_json(response_data)

@router.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
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
            data = await websocket.receive_bytes()
            await deepgram_socket.send(data)

            # print(data)
            asyncio.create_task(deepgram_transcribe(deepgram_socket, websocket))
            

            await manager.broadcast(data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await deepgram_socket.close()