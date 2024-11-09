from fastapi import FastAPI
from websocket import websocket
import ssl

app = FastAPI()

app.include_router(websocket.router)

ssl_context = ssl._create_unverified_context()

@app.get("/")
def read_root():
    return {"Hello": "World"}
