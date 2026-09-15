import importlib
import threading

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