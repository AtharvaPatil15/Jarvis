"""Agent loop: the model chooses tools, results feed back, and the final answer streams out as events."""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from assistant.brain.llm import LLMError, ToolCall
from assistant.brain.session import Session
from assistant.events import AssistantState, Emit, EventType
from assistant.safety.permissions import PermissionGate
from assistant.tools.registry import ToolRegistry

log = logging.getLogger("jarvis.orchestrator")

APOLOGY = "Sorry, my language model is not responding right now."
STEP_LIMIT_REPLY = "I couldn't finish that within my step limit."
EMPTY_REPLY = "I don't have an answer for that."
MAX_TOOL_OUTPUT = 4000


class Orchestrator:
    def __init__(self, llm: Any, registry: ToolRegistry, session: Session, gate: PermissionGate, emit: Emit,
                 memory: Any | None = None, selector: Any | None = None, max_steps: int = 5) -> None:
        self.llm = llm
        self.registry = registry
        self.session = session
        self.gate = gate
        self.memory = memory
        self.selector = selector
        self.max_steps = max_steps
        self.session_id = uuid.uuid4().hex
        self._emit = emit

    async def handle(self, text: str, on_delta: Callable[[str], None] | None = None) -> str:
        text = text.strip()
        if not text:
            return ""
        self._emit(EventType.STATE_CHANGE, AssistantState.THINKING)
        self.session.add_user(text)
        responding = {"on": False}

        def forward(chunk: str) -> None:
            if not responding["on"]:
                responding["on"] = True
                self._emit(EventType.STATE_CHANGE, AssistantState.RESPONDING)
            self._emit(EventType.AI_RESPONSE_DELTA, chunk)
            if on_delta is not None:
                on_delta(chunk)

        try:
            reply = await self._run(text, forward, responding)
        except LLMError as exc:
            log.warning("LLM failure: %s", exc)
            self._emit(EventType.ERROR, {"message": str(exc)})
            reply = APOLOGY
            self.session.add_assistant(reply)
        if not responding["on"]:
            self._emit(EventType.STATE_CHANGE, AssistantState.RESPONDING)
        self._emit(EventType.AI_RESPONSE, reply)
        return reply

    async def _run(self, text: str, forward: Callable[[str], None], responding: dict[str, bool]) -> str:
        names = await asyncio.to_thread(self.selector.select, text, self.registry) if self.selector else None
        schemas = self.registry.schemas(names) or None
        for _ in range(self.max_steps):
            result = await asyncio.to_thread(self.llm.chat, self.session.messages(), tools=schemas, on_delta=forward)
            if not result.tool_calls:
                reply = result.content.strip() or EMPTY_REPLY
                self.session.add_assistant(reply)
                return reply
            self.session.add_assistant(result.content, result.tool_calls)
            for call in result.tool_calls:
                self.session.add_tool_result(call, await self._run_tool(call))
            responding["on"] = False
            self._emit(EventType.STATE_CHANGE, AssistantState.THINKING)
        self.session.add_assistant(STEP_LIMIT_REPLY)
        return STEP_LIMIT_REPLY

    async def _run_tool(self, call: ToolCall) -> str:
        self._emit(EventType.STATE_CHANGE, AssistantState.EXECUTING_TOOL)
        self._emit(EventType.TOOL_START, {"id": call.id, "name": call.name, "arguments": call.arguments})
        ok = False
        tool = self.registry.get(call.name)
        if tool is None:
            output = f"ERROR: unknown tool '{call.name}'"
        else:
            try:
                args = tool.parse_args(call.arguments)
            except ValidationError as exc:
                output = f"ERROR: invalid arguments for {call.name}: {exc.errors(include_url=False)}"
            else:
                if tool.requires_permission and not await self.gate.request(tool.name, tool.permission_summary(args)):
                    output = f"ERROR: the user denied permission for {call.name}"
                else:
                    try:
                        output = await asyncio.to_thread(tool.run, args)
                        ok = not output.startswith("ERROR")
                    except Exception as exc:
                        log.exception("tool %s crashed", call.name)
                        output = f"ERROR: {call.name} failed: {exc}"
        if len(output) > MAX_TOOL_OUTPUT:
            output = output[:MAX_TOOL_OUTPUT] + " [truncated]"
        self._emit(EventType.TOOL_END, {"id": call.id, "name": call.name, "ok": ok, "summary": output[:200]})
        return output