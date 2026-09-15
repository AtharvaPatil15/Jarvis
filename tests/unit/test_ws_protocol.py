import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import server
from assistant.brain.fake_llm import FakeLLM
from assistant.brain.llm import ChatResult, LLMError, ToolCall
from assistant.config import Settings
from assistant.orchestrator import APOLOGY
from assistant.tools.base import BaseTool
from tests.helpers import IDLE, receive_until_idle

pytestmark = pytest.mark.timeout(30)


def fake_settings() -> Settings:
    return Settings(_env_file=None, llm_backend="fake", voice_enabled=False)


def without_deltas(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m["type"] != "ai_response_delta"]


def delta_text(messages: list[dict]) -> str:
    return "".join(m["payload"] for m in messages if m["type"] == "ai_response_delta")


def test_user_text_produces_the_ordered_event_sequence() -> None:
    with TestClient(server.create_app(fake_settings())) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "hello jarvis"})
        received = receive_until_idle(ws)
    assert without_deltas(received) == [
        {"type": "user_transcript", "payload": "hello jarvis"},
        {"type": "state_change", "payload": "thinking"},
        {"type": "state_change", "payload": "responding"},
        {"type": "ai_response", "payload": "You said: hello jarvis"},
        IDLE,
    ]
    assert delta_text(received) == "You said: hello jarvis"


def test_blank_text_is_ignored() -> None:
    with TestClient(server.create_app(fake_settings())) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "   "})
        ws.send_json({"type": "user_text", "payload": "ping"})
        assert ws.receive_json() == {"type": "user_transcript", "payload": "ping"}


def test_invalid_json_reports_error_and_socket_survives() -> None:
    with TestClient(server.create_app(fake_settings())) as client, client.websocket_connect("/ws") as ws:
        ws.send_text("not json")
        assert ws.receive_json() == {
            "type": "error", "payload": {"message": "invalid message: expected JSON {type, payload}"}
        }
        ws.send_json({"type": "user_text", "payload": "still alive"})
        assert without_deltas(receive_until_idle(ws))[-2] == {"type": "ai_response", "payload": "You said: still alive"}


def test_unsupported_message_type_reports_error() -> None:
    with TestClient(server.create_app(fake_settings())) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "dance", "payload": None})
        assert ws.receive_json() == {"type": "error", "payload": {"message": "unsupported message type: dance"}}


def test_invalid_permission_response_reports_error() -> None:
    with TestClient(server.create_app(fake_settings())) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "permission_response", "payload": {"id": 5}})
        assert ws.receive_json() == {"type": "error", "payload": {"message": "invalid permission_response payload"}}


class BrokenLLM(FakeLLM):
    def chat(self, *args, **kwargs):
        raise LLMError("model offline")


def test_model_failure_is_spoken_as_an_apology() -> None:
    app = server.create_app(fake_settings(), llm=BrokenLLM())
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "anything"})
        received = receive_until_idle(ws)
    assert received == [
        {"type": "user_transcript", "payload": "anything"},
        {"type": "state_change", "payload": "thinking"},
        {"type": "error", "payload": {"message": "model offline"}},
        {"type": "state_change", "payload": "responding"},
        {"type": "ai_response", "payload": APOLOGY},
        IDLE,
    ]


class DangerTool(BaseTool):
    name = "danger"
    description = "Needs permission"
    requires_permission = True

    class Args(BaseModel):
        target: str

    def run(self, args) -> str:
        return f"did {args.target}"


def test_permission_round_trip_over_websocket() -> None:
    script = [ChatResult(content="", tool_calls=[ToolCall(id="t1", name="danger", arguments={"target": "notes"})]),
              ChatResult(content="Done.", tool_calls=[])]
    app = server.create_app(fake_settings(), llm=FakeLLM(script=script))
    app.state.registry.register(DangerTool())
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "do the dangerous thing"})
        request = None
        while request is None:
            message = ws.receive_json()
            if message["type"] == "permission_request":
                request = message["payload"]
        assert request["tool"] == "danger"
        assert request["summary"] == 'danger({"target":"notes"})'
        ws.send_json({"type": "permission_response", "payload": {"id": request["id"], "allowed": True}})
        received = receive_until_idle(ws)
    assert [m["payload"] for m in received if m["type"] == "tool_end"] == [
        {"id": "t1", "name": "danger", "ok": True, "summary": "did notes"}
    ]
    assert without_deltas(received)[-2] == {"type": "ai_response", "payload": "Done."}