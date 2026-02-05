import asyncio
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from assistant.voice.voice_controller import VoiceController
from assistant.orchestrator import Orchestrator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()
active_socket: WebSocket | None = None
main_loop: asyncio.AbstractEventLoop | None = None

def handle_voice_event(event_type: str, data: Any):
    """
    Thread-Safe Callback: Pushes updates from Voice Thread to FastAPI Loop.
    """
    print(f"⚡ Event: {event_type} | Data: {data}")
    
    # Bridge Background Thread -> Main Async Loop
    if main_loop and main_loop.is_running():
        # 1. Handle Command Processing
        if event_type == "process_command":
            asyncio.run_coroutine_threadsafe(process_and_respond(data), main_loop)
            return

        # 2. Broadcast to UI
        if active_socket:
            payload = {"type": event_type, "payload": data}
            try:
                asyncio.run_coroutine_threadsafe(active_socket.send_json(payload), main_loop)
            except Exception as e:
                print(f"❌ WebSocket Send Error: {e}")

async def process_and_respond(command: str):
    """Async wrapper to handle LLM processing without blocking"""
    # 1. Generate Response
    response_text = orchestrator.handle_input(command)
    
    # 2. Update UI
    if active_socket:
        await active_socket.send_json({"type": "ai_response", "payload": response_text})
    
    # 3. Speak Response (CRITICAL FIX: Run in Thread Pool to avoid blocking Loop)
    # This prevents the "asyncio.run() cannot be called" error
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, voice.speak, response_text)

voice = VoiceController(on_event=handle_voice_event)

@app.on_event("startup")
async def startup():
    global main_loop
    main_loop = asyncio.get_running_loop()
    voice.start()

@app.on_event("shutdown")
async def shutdown():
    voice.stop()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global active_socket
    await websocket.accept()
    active_socket = websocket
    print("🟢 Desktop UI Connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("🔴 Desktop UI Disconnected")
        active_socket = None