"""Event and state names shared with the UI. Must match docs/PLAN.md §4 and store/assistantStore.ts."""
from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    STATE_CHANGE = "state_change"
    WAKE_WORD_DETECTED = "wake_word_detected"
    USER_TRANSCRIPT = "user_transcript"
    AI_RESPONSE_DELTA = "ai_response_delta"
    AI_RESPONSE = "ai_response"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    PERMISSION_REQUEST = "permission_request"
    REMINDER = "reminder"
    ERROR = "error"


class AssistantState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    RESPONDING = "responding"
    EXECUTING_TOOL = "executing_tool"


Emit = Callable[[str, Any], None]