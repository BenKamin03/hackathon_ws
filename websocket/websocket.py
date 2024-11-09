from typing import List
import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.websockets import WebSocketState
import json
import asyncio
import os
import websockets
import ssl

from assistant import assistant


router = APIRouter()
load_dotenv()

WAKE_WORD = "hey assistant"

# Connection Manager for handling multiple WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.transcript = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_all(self, data: object):
        self.transcript.append(data)
        await asyncio.gather(
            *[connection.send_json(data) for connection in self.active_connections if connection.client_state == WebSocketState.CONNECTED]
        )
        print("sent", json.dumps(data, indent=4))

    async def broadcast(self, data: bytes, sender: WebSocket):
        self.transcript.append(data)
        for connection in self.active_connections:
            if connection != sender and connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_bytes(data)
                except Exception:
                    pass  # Suppress errors during broadcasting

managers = {}

async def text_to_speech(text: str, manager: ConnectionManager):
    """Convert text to speech using the Deepgram TTS API."""
    print("connecting to tts")
    try:
        ssl_context = ssl.SSLContext()
        ssl_context.verify_mode = ssl.CERT_NONE
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.deepgram.com/v1/speak?model=aura-asteria-en',
                headers={
                    'Authorization': f'Token {os.getenv("DEEPGRAM_API_KEY")}',
                    'Content-Type': 'application/json'
                },
                json={"text": text},
                ssl=ssl_context
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    await manager.broadcast(audio_data, sender=None)
                else:
                    print(f"Error: {response.status}")
    except Exception as e:
        print(e)
    

async def deepgram_transcribe(deepgram_socket: websockets.WebSocketClientProtocol, manager: ConnectionManager, data):
    """Receive transcriptions from Deepgram and send to the client WebSocket."""
    try:
        await deepgram_socket.send(data)
        response = await deepgram_socket.recv()
        response_data = json.loads(response)

        transcript = response_data["channel"]["alternatives"][0]['transcript']

        if transcript == '': return

        print(transcript)
        await manager.send_all(response_data)
        if WAKE_WORD.lower() in transcript.lower():
            print("WAKE WORD DETECTED")
            assistant_response = assistant.generate_text(transcript)
            
            await manager.send_all({
                "assistant_response": assistant_response
            })

            await text_to_speech(assistant_response, manager)
            

    except Exception:
        pass  # Suppress any errors to avoid printing task errors

@router.websocket("/ws/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str):
    
    # TODO Add authentication logic here
    # use meeting id to find the meeting in the database
    # check if the user is allowed to join the meeting by using the user id
    # if the user is allowed to join the meeting, then allow the user to connect to the websocket
    # else return an error message
    # with the user id, store it in the connection manager to keep track of the user. this will be important to tell who is speaking


    if meeting_id not in managers:
        managers[meeting_id] = ConnectionManager()

    manager = managers[meeting_id]

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
            asyncio.create_task(deepgram_transcribe(deepgram_socket, manager, data))

            # Broadcast the data to other clients
            await manager.broadcast(data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await deepgram_socket.close()

        if len(manager.active_connections) == 0:
            del managers[meeting_id]
    except Exception:
        pass  # Suppress other exceptions to avoid unwanted prints