import re
from pathlib import Path

from assistant.events import AssistantState, EventType

ROOT = Path(__file__).resolve().parents[2]


def test_assistant_states_match_frontend_store() -> None:
    source = (ROOT / "store" / "assistantStore.ts").read_text(encoding="utf-8")
    union = re.search(r"export type AssistantStatus\s*=\s*([^;]+);", source)
    assert union, "AssistantStatus union not found in store/assistantStore.ts"
    assert set(re.findall(r"'([a-z_]+)'", union.group(1))) == {s.value for s in AssistantState}


def test_event_types_match_protocol_table() -> None:
    assert {e.value for e in EventType} == {
        "state_change", "wake_word_detected", "user_transcript", "ai_response_delta", "ai_response",
        "tool_start", "tool_end", "permission_request", "reminder", "error",
    }


def test_enum_members_behave_as_plain_strings() -> None:
    assert EventType.STATE_CHANGE == "state_change"
    assert f"{AssistantState.EXECUTING_TOOL}" == "executing_tool"
    assert str(AssistantState.IDLE) == "idle"