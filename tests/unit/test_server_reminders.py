from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings

pytestmark = pytest.mark.timeout(30)


def test_due_reminder_is_pushed_to_the_ui() -> None:
    app = server.create_app(Settings(_env_file=None, llm_backend="fake", voice_enabled=False))
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        reminder_id = app.state.scheduler.schedule("drink water", datetime.now(timezone.utc) - timedelta(seconds=1))
        app.state.scheduler.check_now()
        assert ws.receive_json() == {"type": "reminder", "payload": {"id": reminder_id, "text": "drink water"}}