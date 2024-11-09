from fastapi import FastAPI
from websocket import websocket

app = FastAPI()

app.include_router(websocket.router)

@app.get("/")
def read_root():
    return {"Hello": "World"}
