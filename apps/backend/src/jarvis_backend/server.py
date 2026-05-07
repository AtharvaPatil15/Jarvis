import asyncio
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from jarvis_backend.orchestrator import Orchestrator
from jarvis_backend.voice.conversation_manager import ConversationManager
from jarvis_backend.voice.voice_controller import VoiceController


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
    global current_llm_task

    if not main_loop or not main_loop.is_running():
        return

    if event_type in {"process_command", "merge_command"}:
        if current_llm_task and not current_llm_task.done():
            current_llm_task.cancel()
        current_llm_task = asyncio.run_coroutine_threadsafe(process_and_respond(data), main_loop)
        return

    if active_socket:
        payload = {"type": event_type, "payload": data}
        try:
            asyncio.run_coroutine_threadsafe(active_socket.send_json(payload), main_loop)
        except Exception as exc:
            print(f"WebSocket send error: {exc}")


async def process_and_respond(command: str):
    try:
        response_data = orchestrator.handle_input(command)

        if isinstance(response_data, dict):
            response_text = response_data.get("content", "I encountered an error.")
            tool_used = response_data.get("tool")
        else:
            response_text = str(response_data)
            tool_used = None

        if active_socket:
            await active_socket.send_json({"type": "ai_response", "payload": response_text})
            if tool_used:
                await active_socket.send_json({"type": "state_change", "payload": "executing_tool"})

        delay = 0.5
        if len(response_text) > 120:
            delay = 1.2
        elif len(response_text) > 60:
            delay = 0.8
        await asyncio.sleep(delay)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, voice.speak, response_text)

        if voice.conv_manager:
            voice.conv_manager.is_processing = False

    except asyncio.CancelledError:
        if voice.conv_manager:
            voice.conv_manager.is_processing = False
        raise


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
    print("Desktop UI connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("Desktop UI disconnected")
        active_socket = None
