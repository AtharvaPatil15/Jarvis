import assistant


def test_assistant_package_importable() -> None:
    assert assistant is not None


def test_event_recorder_records_in_order(events) -> None:
    events("state_change", "thinking")
    events("ai_response", "hi")
    events("state_change", "idle")
    assert events.types() == ["state_change", "ai_response", "state_change"]
    assert events.payloads("state_change") == ["thinking", "idle"]