# server.py
import asyncio
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from assistant.voice.voice_controller import VoiceController
from assistant.voice.conversation_manager import ConversationManager
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
current_llm_task: asyncio.Future | None = None

def handle_voice_event(event_type: str, data: Any):
    """
    Thread-Safe Callback: Pushes updates from Voice Thread to FastAPI Loop.
    """
    print(f"⚡ Event: {event_type} | Data: {data}")
    
    # Bridge Background Thread -> Main Async Loop
    if main_loop and main_loop.is_running():
        # 1. Handle Command Processing
        if event_type == "process_command":
            global current_llm_task
            
            # Cancel any ongoing LLM task
            if current_llm_task and not current_llm_task.done():
                current_llm_task.cancel()
            
            current_llm_task = asyncio.run_coroutine_threadsafe(
                process_and_respond(data),
                main_loop
            )
            return
        
        # Handle merge commands (interrupts)
        if event_type == "merge_command":
            if current_llm_task and not current_llm_task.done():
                current_llm_task.cancel()
            
            current_llm_task = asyncio.run_coroutine_threadsafe(
                process_and_respond(data),
                main_loop
            )
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
    try:
        # 1. Generate Response (Now returns a Dict)
        response_data = orchestrator.handle_input(command)
        
        response_text = response_data.get("content", "I encountered an error.")
        tool_used = response_data.get("tool", None)

        # 2. Update UI
        if active_socket:
            await active_socket.send_json({"type": "ai_response", "payload": response_text})
            if tool_used:
                 await active_socket.send_json({"type": "state_change", "payload": "executing_tool"})

        # 3. Speak Response
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, voice.speak, response_text)
        
        # 4. Mark processing complete
        # ✅ This now works because we injected the manager below
        if voice.conv_manager:
            voice.conv_manager.is_processing = False
        
    except asyncio.CancelledError:
        print("⚠️ LLM task cancelled (user interrupted)")
        if voice.conv_manager:
            voice.conv_manager.is_processing = False
        raise

# ✅ FIX: Initialize Manager and Inject into Controller
conv_manager = ConversationManager()
voice = VoiceController(on_event=handle_voice_event)
voice.conv_manager = conv_manager

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