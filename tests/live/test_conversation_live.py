import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from tests.helpers import receive_until_idle

pytestmark = [pytest.mark.live, pytest.mark.timeout(900)]


def ask(ws, text: str) -> tuple[list[str], str]:
    ws.send_json({"type": "user_text", "payload": text})
    messages = receive_until_idle(ws, limit=5000)
    tools = [m["payload"]["name"] for m in messages if m["type"] == "tool_start"]
    reply = next(m["payload"] for m in reversed(messages) if m["type"] == "ai_response")
    return tools, reply


@pytest.fixture(scope="module")
def ws():
    app = server.create_app(Settings(_env_file=None, voice_enabled=False))
    with TestClient(app) as client, client.websocket_connect("/ws") as socket:
        yield socket


def test_time_question_uses_get_time(ws) -> None:
    tools, reply = ask(ws, "What time is it right now?")
    assert "get_time" in tools and reply


def test_maths_then_follow_up_uses_history(ws) -> None:
    tools, reply = ask(ws, "What is 17 times 23?")
    assert "calculate" in tools and "391" in reply.replace(",", "")
    _, follow_up = ask(ws, "Now double that number.")
    assert "782" in follow_up.replace(",", "")


def test_weather_question_uses_get_weather(ws) -> None:
    tools, _ = ask(ws, "What's the weather like at home today?")
    assert "get_weather" in tools


def test_web_question_uses_web_search(ws) -> None:
    tools, _ = ask(ws, "Search the web and tell me what the Python programming language is.")
    assert "web_search" in tools