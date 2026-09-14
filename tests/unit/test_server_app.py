import importlib
import sys
import threading
import types

import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from tests.helpers import wait_until

pytestmark = pytest.mark.timeout(30)


def fake_settings(**overrides) -> Settings:
    values = {"llm_backend": "fake", "voice_enabled": False} | overrides
    return Settings(_env_file=None, **values)


def test_importing_server_builds_nothing() -> None:
    module = importlib.reload(server)
    for name in ("app", "voice", "orchestrator", "active_socket"):
        assert not hasattr(module, name), name


def test_health_with_fake_llm_and_voice_disabled() -> None:
    with TestClient(server.create_app(fake_settings())) as client:
        assert client.get("/health").json() == {"status": "ok", "llm": True, "voice": False}


def test_websocket_connect_and_disconnect_are_tracked() -> None:
    app = server.create_app(fake_settings())
    with TestClient(app) as client:
        with client.websocket_connect("/ws"):
            wait_until(lambda: app.state.hub.client_count == 1)
        wait_until(lambda: app.state.hub.client_count == 0)


def test_emit_from_background_thread_reaches_websocket() -> None:
    app = server.create_app(fake_settings())
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        wait_until(lambda: app.state.hub.client_count == 1)
        worker = threading.Thread(target=app.state.hub.emit, args=("state_change", "idle"))
        worker.start()
        worker.join()
        assert ws.receive_json() == {"type": "state_change", "payload": "idle"}


def test_mark_voice_idle_tolerates_missing_manager_and_resets_flag() -> None:
    server.mark_voice_idle(object())

    class Manager:
        is_processing = True

    class Voice:
        conv_manager = Manager()

    voice = Voice()
    server.mark_voice_idle(voice)
    assert voice.conv_manager.is_processing is False


def test_voice_failure_at_startup_does_not_crash_server(monkeypatch) -> None:
    broken = types.ModuleType("assistant.voice.voice_controller")

    class Exploding:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("no microphone")

    broken.VoiceController = Exploding
    monkeypatch.setitem(sys.modules, "assistant.voice.voice_controller", broken)
    with TestClient(server.create_app(fake_settings(voice_enabled=True))) as client:
        assert client.get("/health").json()["voice"] is False