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
from firebase.firebase_connection import FirebaseConnection
import traceback

router = APIRouter()
load_dotenv()

WAKE_WORD = "okay flux"
firebase = FirebaseConnection()
managers = {}

class ConnectionManager:
    def __init__(self, meeting_id):
        self.active_connections: List[WebSocket] = []
        self.transcript = []
        self.meeting_id = meeting_id
        self.tags = [tag["name"] for tag in firebase.get_tags(meeting_id)]

        self.user_ids = firebase.get_meeting_users(meeting_id)
        self.authenticated_sockets: List[WebSocket] = []
        self.authenticated_ids = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.broadcast(json.dumps({"user_id": self.authenticated_ids[self.authenticated_sockets.index(websocket)], "message": "left"}).encode(), sender=None)

            print("disconnected")
            print(len(self.active_connections))

            if len(self.active_connections) == 0:
                transcript_text = "".join([data["channel"]["alternatives"][0]['transcript'] for data in self.transcript])

                print(transcript_text)

                summary = assistant.get_summary(transcript_text)
                tagline = assistant.get_tagline(transcript_text)
                tags = assistant.get_tags(transcript_text, self.tags)
                kanban = assistant.get_kanban(transcript_text)

                firebase.add_meeting_data(self.meeting_id, {
                    "summary": summary,
                    "tagline": tagline,
                    "tags": tags,
                    "kanban": kanban,
                    "transcript": transcript_text
                })

                print("Ended meeting")

                del self
    def is_authed(self, websocket: WebSocket):
        return websocket in self.authenticated_sockets

    async def send_all(self, data: object):
        self.transcript.append(data)
        await asyncio.gather(
            *[connection.send_json(data) for connection in self.authenticated_sockets if connection.client_state == WebSocketState.CONNECTED]
        )
        print("sent", json.dumps(data, indent=4))

    async def broadcast(self, data: bytes, sender: WebSocket):
        for connection in self.authenticated_sockets:
            if connection != sender and connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_bytes(data)
                except Exception:
                    pass  # Suppress errors during broadcasting

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
        if WAKE_WORD.lower() in transcript.lower().replace(".", "").replace(",", "").replace("!", "").replace("?", "").replace(":", "").replace(";", "").replace("-", "").replace("'", "").replace("\"", "").replace("(", "").replace(")", "").replace("[", "").replace("]", "").replace("{", "").replace("}", "").replace("/", "").replace("\\", "").replace("|", "").replace("@", "").replace("#", "").replace("$", "").replace("%", "").replace("^", "").replace("&", "").replace("*", "").replace("_", "").replace("+", "").replace("=", "").replace("<", "").replace(">", "").replace("`", "").replace("~", "").replace("", ""):
            print("WAKE WORD DETECTED")
            transcript_text = "".join([data["channel"]["alternatives"][0]['transcript'] for data in manager.transcript])
            assistant_response = assistant.use_assistant(transcript_text)
            
            await manager.send_all({
                "assistant_response": assistant_response
            })

            await text_to_speech(assistant_response, manager)
            

    except Exception:
        pass  # Suppress any errors to avoid printing task errors

@router.websocket("/ws/meeting/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str):
    print(meeting_id)

    if meeting_id not in managers:
        managers[meeting_id] = ConnectionManager(meeting_id)

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
        if not manager.is_authed(websocket):
            credentials = await websocket.receive_json()

            print(credentials)

            if not str(credentials["user_id"]) in manager.user_ids:
                await websocket.send_json({"error": "Unauthorized"})
                await websocket.close()
                return
            
            manager.authenticated_sockets.append(websocket)
            manager.authenticated_ids.append(credentials["user_id"])
            await websocket.send_json({"auth": "success"})
            manager.broadcast(json.dumps({"user_id": credentials["user_id"], "message": "joined"}).encode(), sender=websocket)

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
    except Exception as e:
        print("Exception occurred:", traceback.format_exc())
        pass  # Suppress other exceptions to avoid unwanted prints