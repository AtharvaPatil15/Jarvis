from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from assistant.scheduler import ReminderScheduler
from assistant.tools.base import BaseTool

_CLOCK = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)")
_FORMAT = "%a %d %b %I:%M %p"


class SetReminderArgs(BaseModel):
    text: str = Field(description="What to remind the user about")
    in_minutes: int | None = Field(default=None, ge=1, le=10080, description="Minutes from now")
    at_time: str | None = Field(default=None, description="Clock time in 24-hour HH:MM")
    day: Literal["today", "tomorrow"] = "today"


class SetReminderTool(BaseTool):
    name = "set_reminder"
    description = "Set a reminder either in_minutes from now or at_time (HH:MM, 24-hour) today or tomorrow."
    Args = SetReminderArgs

    def __init__(self, scheduler: ReminderScheduler, timezone: str,
                 now: Callable[[], datetime] | None = None) -> None:
        self._scheduler = scheduler
        self._zone = ZoneInfo(timezone)
        self._now = now or (lambda: datetime.now(self._zone))

    def run(self, args: SetReminderArgs) -> str:
        if (args.in_minutes is None) == (args.at_time is None):
            return "ERROR: give exactly one of in_minutes or at_time"
        now = self._now()
        if args.in_minutes is not None:
            due = now + timedelta(minutes=args.in_minutes)
        else:
            match = _CLOCK.fullmatch(args.at_time.strip())
            if not match:
                return f"ERROR: at_time must be HH:MM, got {args.at_time!r}"
            due = now.replace(hour=int(match.group(1)), minute=int(match.group(2)), second=0, microsecond=0)
            if args.day == "tomorrow":
                due += timedelta(days=1)
            elif due <= now:
                return "ERROR: that time has already passed today; use day='tomorrow'"
        reminder_id = self._scheduler.schedule(args.text, due)
        return f"Reminder {reminder_id} set for {due.astimezone(self._zone).strftime(_FORMAT)}: {args.text}"


class ListRemindersArgs(BaseModel):
    pass


class ListRemindersTool(BaseTool):
    name = "list_reminders"
    description = "List the user's upcoming reminders."
    Args = ListRemindersArgs

    def __init__(self, scheduler: ReminderScheduler, timezone: str) -> None:
        self._scheduler = scheduler
        self._zone = ZoneInfo(timezone)

    def run(self, args: ListRemindersArgs) -> str:
        pending = self._scheduler.pending()
        if not pending:
            return "No upcoming reminders."
        return "\n".join(f"{i}: {text} at {due.astimezone(self._zone).strftime(_FORMAT)}" for i, text, due in pending)