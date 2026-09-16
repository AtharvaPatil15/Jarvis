import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from assistant.memory.db import MemoryDB
from tests.helpers import IDLE

pytestmark = [pytest.mark.live, pytest.mark.timeout(900)]


def converse(settings: Settings, utterances: list[str], approve: bool = True) -> list[str]:
    app = server.create_app(settings)
    replies: list[str] = []
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        for text in utterances:
            ws.send_json({"type": "user_text", "payload": text})
            while True:
                message = ws.receive_json()
                if message["type"] == "permission_request":
                    ws.send_json({"type": "permission_response",
                                  "payload": {"id": message["payload"]["id"], "allowed": approve}})
                elif message["type"] == "ai_response":
                    replies.append(message["payload"])
                elif message == IDLE:
                    break
        client.portal.call(app.state.orchestrator.wait_background)
    return replies


def teal_facts(settings: Settings) -> list[str]:
    db = MemoryDB(settings.data_dir / "jarvis.db")
    try:
        return [text for _, text, _ in db.all_facts() if "teal" in text.lower()]
    finally:
        db.close()


def test_memory_survives_restart_and_can_be_forgotten(tmp_path) -> None:
    settings = Settings(_env_file=None, voice_enabled=False, data_dir=tmp_path / "data")
    converse(settings, ["Please remember that my favourite colour is teal."])
    assert teal_facts(settings), "fact was not stored"
    (answer,) = converse(settings, ["What is my favourite colour?"])
    assert "teal" in answer.lower()
    converse(settings, ["Please forget my favourite colour."])
    assert teal_facts(settings) == []
