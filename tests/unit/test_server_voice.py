import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from tests.helpers import receive_until_idle

pytestmark = pytest.mark.timeout(30)


class FakeVoice:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.running = False
        self.stopped = False

    async def run(self, stop) -> None:
        self.running = True
        await stop.wait()
        self.stopped = True

    async def speak(self, text: str) -> None:
        self.spoken.append(text)


def voice_settings() -> Settings:
    return Settings(_env_file=None, llm_backend="fake", voice_enabled=True)


@pytest.fixture
def fake_voice(monkeypatch) -> FakeVoice:
    import assistant.voice.factory as factory

    voice = FakeVoice()
    monkeypatch.setattr(factory, "build_voice_controller", lambda settings, handler, emit: voice)
    return voice


def test_voice_loop_starts_and_stops_with_the_server(fake_voice) -> None:
    with TestClient(server.create_app(voice_settings())) as client:
        assert client.get("/health").json()["voice"] is True
        assert fake_voice.running
    assert fake_voice.stopped


def test_typed_commands_are_spoken_when_voice_is_on(fake_voice) -> None:
    with TestClient(server.create_app(voice_settings())) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "hello"})
        receive_until_idle(ws)
    assert fake_voice.spoken == ["You said: hello"]


def test_voice_handler_streams_through_the_orchestrator(fake_voice) -> None:
    app = server.create_app(voice_settings())
    chunks: list[str] = []
    with TestClient(app) as client:
        reply = client.portal.call(app.state.voice_handler, "hi there", chunks.append)
    assert reply == "You said: hi there"
    assert "".join(chunks) == reply


def test_voice_pipeline_failure_keeps_text_mode_working(monkeypatch) -> None:
    import assistant.voice.factory as factory

    def boom(*args, **kwargs):
        raise RuntimeError("no microphone found")

    monkeypatch.setattr(factory, "build_voice_controller", boom)
    with TestClient(server.create_app(voice_settings())) as client:
        assert client.get("/health").json() == {"status": "ok", "llm": True, "voice": False}
