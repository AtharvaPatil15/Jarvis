"""JARVIS backend. Run: .venv/Scripts/python.exe -m uvicorn server:create_app --factory --host 127.0.0.1 --port 8000"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from assistant.config import Settings, get_settings
from assistant.events import AssistantState, EventType
from assistant.hub import ConnectionHub
from assistant.runtime import build_runtime
from assistant.safety.permissions import WebSocketPermissionGate

log = logging.getLogger("jarvis.server")


def mark_voice_idle(voice: Any) -> None:
    manager = getattr(voice, "conv_manager", None)
    if manager is not None:
        manager.is_processing = False


def _valid_permission_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("id"), str) and isinstance(payload.get("allowed"), bool)


def create_app(settings: Settings | None = None, *, llm: Any | None = None,
               enable_voice: bool | None = None) -> FastAPI:
    settings = settings or get_settings()
    voice_wanted = settings.voice_enabled if enable_voice is None else enable_voice
    hub = ConnectionHub()
    gate = WebSocketPermissionGate(hub.emit, timeout_s=settings.permission_timeout_s)
    runtime = build_runtime(settings, hub.emit, gate, llm=llm)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hub.bind_loop(asyncio.get_running_loop())
        if voice_wanted:
            try:
                from assistant.voice.voice_controller import VoiceController

                voice = VoiceController(on_event=on_voice_event)
                voice.start()
                app.state.voice = voice
            except Exception:
                log.exception("voice disabled: voice controller failed to start")
                app.state.voice = None
        try:
            yield
        finally:
            if app.state.voice is not None:
                app.state.voice.stop()
            await hub.close()

    app = FastAPI(title="JARVIS", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.hub = hub
    app.state.settings = settings
    app.state.llm = runtime.llm
    app.state.registry = runtime.registry
    app.state.orchestrator = runtime.orchestrator
    app.state.gate = gate
    app.state.voice = None
    lock = asyncio.Lock()

    async def process_text(text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        async with lock:
            hub.emit(EventType.USER_TRANSCRIPT, text)
            try:
                reply = await runtime.orchestrator.handle(text)
            except Exception as exc:
                log.exception("command failed")
                hub.emit(EventType.ERROR, {"message": str(exc)})
                hub.emit(EventType.STATE_CHANGE, AssistantState.IDLE)
                return ""
            voice = app.state.voice
            if voice is not None:
                await asyncio.to_thread(voice.speak, reply)
                mark_voice_idle(voice)
            hub.emit(EventType.STATE_CHANGE, AssistantState.IDLE)
            return reply

    app.state.process_text = process_text

    def on_voice_event(event_type: str, data: Any) -> None:
        if event_type in ("process_command", "merge_command"):
            asyncio.run_coroutine_threadsafe(app.state.process_text(str(data)), hub.loop)
            return
        hub.emit(event_type, data)
        if event_type == EventType.WAKE_WORD_DETECTED:
            hub.emit(EventType.STATE_CHANGE, AssistantState.LISTENING)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        check = getattr(app.state.llm, "health", None)
        llm_ok = bool(await asyncio.to_thread(check)) if callable(check) else False
        return {"status": "ok", "llm": llm_ok, "voice": app.state.voice is not None}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await hub.connect(ws)
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    message = json.loads(raw)
                    kind, payload = message["type"], message.get("payload")
                except (ValueError, KeyError, TypeError):
                    hub.emit(EventType.ERROR, {"message": "invalid message: expected JSON {type, payload}"})
                    continue
                if kind == "user_text" and isinstance(payload, str):
                    asyncio.create_task(app.state.process_text(payload))
                elif kind == "permission_response":
                    if _valid_permission_payload(payload):
                        gate.resolve(payload["id"], payload["allowed"])
                    else:
                        hub.emit(EventType.ERROR, {"message": "invalid permission_response payload"})
                else:
                    hub.emit(EventType.ERROR, {"message": f"unsupported message type: {kind}"})
        except WebSocketDisconnect:
            pass
        finally:
            hub.disconnect(ws)

    return app