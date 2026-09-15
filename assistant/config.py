"""Typed settings for JARVIS. Every tunable value lives here; override with JARVIS_* env vars or .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_file_roots() -> list[Path]:
    home = Path.home()
    return [home / "Documents", home / "Desktop", home / "Downloads"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_", env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore")

    ollama_url: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen3:8b"
    embed_model: str = "nomic-embed-text"
    llm_backend: Literal["ollama", "fake"] = "ollama"
    llm_timeout_s: float = 120.0
    llm_disable_thinking: bool = True

    user_description: str = "Final-year engineering student"
    location_name: str = "Pimpri-Chinchwad, Maharashtra, India"
    latitude: float = 18.6298
    longitude: float = 73.7997
    timezone: str = "Asia/Kolkata"

    data_dir: Path = Path("data")
    models_dir: Path = Path("models")

    whisper_model: str = "small.en"
    whisper_device: Literal["auto", "cuda", "cpu"] = "auto"
    tts_voice: str = "bm_george"
    tts_speed: float = 1.1
    wake_model: str = "hey_jarvis"
    wake_threshold: float = 0.5
    vad_silence_ms: int = 600
    voice_enabled: bool = True

    server_host: str = "127.0.0.1"
    server_port: int = 8000

    max_agent_steps: int = 5
    history_max_chars: int = 12000
    permission_timeout_s: float = 30.0
    file_roots: list[Path] = Field(default_factory=_default_file_roots)
    mcp_config_path: Path = Path("mcp_servers.json")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()