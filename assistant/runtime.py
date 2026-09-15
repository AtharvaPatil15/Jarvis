"""Builds the assistant components shared by the server and the terminal CLI."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from assistant.brain.llm import LLMClient
from assistant.brain.prompts import build_system_prompt
from assistant.brain.session import Session
from assistant.config import Settings
from assistant.events import Emit
from assistant.orchestrator import Orchestrator
from assistant.safety.permissions import PermissionGate
from assistant.tools.builtin import build_default_registry
from assistant.tools.registry import ToolRegistry


@dataclass
class Runtime:
    settings: Settings
    llm: Any
    registry: ToolRegistry
    session: Session
    orchestrator: Orchestrator


def build_llm(settings: Settings) -> Any:
    if settings.llm_backend == "fake":
        from assistant.brain.fake_llm import FakeLLM

        return FakeLLM()
    return LLMClient(settings.ollama_url, settings.chat_model, settings.embed_model,
                     timeout_s=settings.llm_timeout_s, disable_thinking=settings.llm_disable_thinking)


def build_runtime(settings: Settings, emit: Emit, gate: PermissionGate, llm: Any | None = None) -> Runtime:
    llm = llm if llm is not None else build_llm(settings)
    registry = build_default_registry(settings)
    zone = ZoneInfo(settings.timezone)
    session = Session(lambda: build_system_prompt(settings, datetime.now(zone)), max_chars=settings.history_max_chars)
    orchestrator = Orchestrator(llm, registry, session, gate, emit, max_steps=settings.max_agent_steps)
    return Runtime(settings=settings, llm=llm, registry=registry, session=session, orchestrator=orchestrator)