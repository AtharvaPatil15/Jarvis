import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings

pytestmark = pytest.mark.timeout(30)
IDLE = {"type": "state_change", "payload": "idle"}


def fake_app():
    return server.create_app(Settings(_env_file=None, llm_backend="fake", voice_enabled=False))


def receive_until_idle(ws, limit: int = 20) -> list[dict]:
    received = []
    for _ in range(limit):
        message = ws.receive_json()
        received.append(message)
        if message == IDLE:
            return received
    raise AssertionError(f"no idle within {limit} messages: {received}")


def test_user_text_produces_the_ordered_event_sequence() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "hello jarvis"})
        assert receive_until_idle(ws) == [
            {"type": "user_transcript", "payload": "hello jarvis"},
            {"type": "state_change", "payload": "thinking"},
            {"type": "state_change", "payload": "responding"},
            {"type": "ai_response", "payload": "You said: hello jarvis"},
            IDLE,
        ]


def test_blank_text_is_ignored() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "   "})
        ws.send_json({"type": "user_text", "payload": "ping"})
        assert ws.receive_json() == {"type": "user_transcript", "payload": "ping"}


def test_invalid_json_reports_error_and_socket_survives() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_text("not json")
        assert ws.receive_json() == {
            "type": "error", "payload": {"message": "invalid message: expected JSON {type, payload}"}
        }
        ws.send_json({"type": "user_text", "payload": "still alive"})
        assert receive_until_idle(ws)[-2] == {"type": "ai_response", "payload": "You said: still alive"}


def test_unsupported_message_type_reports_error() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "dance", "payload": None})
        assert ws.receive_json() == {"type": "error", "payload": {"message": "unsupported message type: dance"}}


def test_model_failure_emits_error_then_idle(monkeypatch) -> None:
    app = fake_app()

    def boom(prompt: str) -> str:
        raise RuntimeError("model offline")

    monkeypatch.setattr(app.state.llm, "generate", boom)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "anything"})
        assert receive_until_idle(ws) == [
            {"type": "user_transcript", "payload": "anything"},
            {"type": "state_change", "payload": "thinking"},
            {"type": "error", "payload": {"message": "model offline"}},
            IDLE,
        ]