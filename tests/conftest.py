from __future__ import annotations

from typing import Any

import pytest


class EventRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def __call__(self, type_: str, payload: Any) -> None:
        self.events.append((str(type_), payload))

    def types(self) -> list[str]:
        return [t for t, _ in self.events]

    def payloads(self, type_: str) -> list[Any]:
        return [p for t, p in self.events if t == str(type_)]


@pytest.fixture
def events() -> EventRecorder:
    return EventRecorder()