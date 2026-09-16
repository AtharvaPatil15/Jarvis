"""Builds the assistant components shared by the server and the terminal CLI."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from assistant.brain.llm import LLMClient
from assistant.brain.prompts import build_system_prompt
from assistant.brain.session import Session
from assistant.config import Settings
from assistant.events import Emit, EventType
from assistant.memory.db import MemoryDB
from assistant.memory.manager import MemoryManager
from assistant.orchestrator import Orchestrator
from assistant.safety.permissions import PermissionGate
from assistant.scheduler import ReminderScheduler
from assistant.tools.builtin import build_default_registry
from assistant.tools.registry import ToolRegistry


@dataclass
class Runtime:
    settings: Settings
    llm: Any
    registry: ToolRegistry
    session: Session
    orchestrator: Orchestrator
    db: MemoryDB
    memory: MemoryManager
    scheduler: ReminderScheduler
    reminder_listeners: list[Callable[[int, str], None]]


def build_llm(settings: Settings) -> Any:
    if settings.llm_backend == "fake":
        from assistant.brain.fake_llm import FakeLLM

        return FakeLLM()
    return LLMClient(settings.ollama_url, settings.chat_model, settings.embed_model,
                     timeout_s=settings.llm_timeout_s, disable_thinking=settings.llm_disable_thinking)


def build_runtime(settings: Settings, emit: Emit, gate: PermissionGate, llm: Any | None = None) -> Runtime:
    llm = llm if llm is not None else build_llm(settings)
    db = MemoryDB(settings.data_dir / "jarvis.db")
    memory = MemoryManager(db, llm)

    listeners: list[Callable[[int, str], None]] = []

    def fire(reminder_id: int, text: str) -> None:
        emit(EventType.REMINDER, {"id": reminder_id, "text": text})
        for listener in list(listeners):
            listener(reminder_id, text)

    scheduler = ReminderScheduler(db, fire)

    registry = build_default_registry(settings, memory=memory, scheduler=scheduler)
    zone = ZoneInfo(settings.timezone)
    box: dict[str, Orchestrator] = {}
    session = Session(lambda: build_system_prompt(settings, datetime.now(zone), box["orchestrator"].current_memories),
                      max_chars=settings.history_max_chars)
    orchestrator = Orchestrator(llm, registry, session, gate, emit, memory=memory, max_steps=settings.max_agent_steps)
    box["orchestrator"] = orchestrator
    return Runtime(settings=settings, llm=llm, registry=registry, session=session, orchestrator=orchestrator,
                   db=db, memory=memory, scheduler=scheduler, reminder_listeners=listeners)
