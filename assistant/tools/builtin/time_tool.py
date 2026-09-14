from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from assistant.tools.base import BaseTool


class GetTimeArgs(BaseModel):
    pass


class GetTimeTool(BaseTool):
    name = "get_time"
    description = "Get the current local date, weekday and time."
    Args = GetTimeArgs

    def __init__(self, timezone: str = "Asia/Kolkata", now: Callable[[], datetime] | None = None) -> None:
        self._zone = ZoneInfo(timezone)
        self._now = now or (lambda: datetime.now(self._zone))

    def run(self, args: GetTimeArgs) -> str:
        return f"{self._now().strftime('%A, %d %B %Y, %I:%M %p')} ({self._zone.key})"