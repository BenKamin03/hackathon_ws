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

router = APIRouter()
load_dotenv()

# Deepgram API key
DEEPGRAM_WS_URL = f"wss://api.deepgram.com/v1/listen?access_token={os.getenv('DEEPGRAM_API_KEY')}&punctuate=true"

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

@router.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await stream_to_deepgram(websocket)

async def stream_to_deepgram(websocket: WebSocket):
    """
    Connects to Deepgram WebSocket API and streams audio data received
    from the client WebSocket.
    """
    try:
        async with websockets.connect(DEEPGRAM_WS_URL) as deepgram_ws:
            print("Connected to Deepgram WebSocket")

            async def forward_audio():
                # Continuously receive audio data from the client and send to Deepgram
                while websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        audio_chunk = await websocket.receive_bytes()
                        await deepgram_ws.send(audio_chunk)
                    except WebSocketDisconnect:
                        print("Client disconnected")
                        break
                    except Exception as e:
                        print(f"Error forwarding audio to Deepgram: {e}")
                        break

            async def receive_transcription():
                # Continuously receive transcription results from Deepgram and send to client
                while True:
                    try:
                        response = await deepgram_ws.recv()
                        data = json.loads(response)
                        # Extract the transcript if available
                        transcript = data.get('channel', {}).get('alternatives', [{}])[0].get('transcript', '')
                        if transcript:
                            await websocket.send_text(transcript)
                    except Exception as e:
                        print(f"Error receiving transcription: {e}")
                        break

            # Run both tasks concurrently
            await asyncio.gather(forward_audio(), receive_transcription())

    except Exception as e:
        print(f"Error connecting to Deepgram WebSocket: {e}")
