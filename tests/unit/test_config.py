from pathlib import Path

from assistant.config import Settings, get_settings


def test_defaults_match_plan() -> None:
    s = Settings(_env_file=None)
    assert s.ollama_url == "http://127.0.0.1:11434"
    assert s.chat_model == "qwen3:8b"  # change only if P0-T3 recorded a different model in DECISIONS.md
    assert s.embed_model == "nomic-embed-text"
    assert s.llm_backend == "ollama"
    assert s.max_agent_steps == 5
    assert s.server_host == "127.0.0.1"
    assert s.server_port == 8000
    assert s.whisper_model == "small.en"
    assert s.wake_model == "hey_jarvis"
    assert Path.home() / "Documents" in s.file_roots
    assert s.porcupine_access_key == ""


def test_env_prefix_overrides(monkeypatch) -> None:
    monkeypatch.setenv("JARVIS_CHAT_MODEL", "test-model")
    monkeypatch.setenv("JARVIS_VOICE_ENABLED", "false")
    monkeypatch.setenv("JARVIS_MAX_AGENT_STEPS", "3")
    s = Settings(_env_file=None)
    assert s.chat_model == "test-model"
    assert s.voice_enabled is False
    assert s.max_agent_steps == 3


def test_unprefixed_env_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("CHAT_MODEL", "should-not-apply")
    assert Settings(_env_file=None).chat_model != "should-not-apply"


def test_works_without_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert Settings().chat_model


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()