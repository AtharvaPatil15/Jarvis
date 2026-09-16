from datetime import datetime
from zoneinfo import ZoneInfo

from assistant.config import Settings
from assistant.memory.db import MemoryDB
from assistant.scheduler import ReminderScheduler
from assistant.tools.builtin import build_default_registry
from assistant.tools.builtin.reminders import ListRemindersTool, SetReminderTool

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 9, 13, 17, 5, tzinfo=IST)


def tools(tmp_path):
    scheduler = ReminderScheduler(MemoryDB(tmp_path / "m.db"), lambda i, t: None)
    return SetReminderTool(scheduler, "Asia/Kolkata", now=lambda: NOW), ListRemindersTool(scheduler, "Asia/Kolkata")


def run(tool, **arguments) -> str:
    return tool.run(tool.parse_args(arguments))


def test_relative_and_clock_time_reminders(tmp_path) -> None:
    set_tool, list_tool = tools(tmp_path)
    assert run(set_tool, text="stretch", in_minutes=30) == "Reminder 1 set for Sun 13 Sep 05:35 PM: stretch"
    assert run(set_tool, text="call mom", at_time="18:30") == "Reminder 2 set for Sun 13 Sep 06:30 PM: call mom"
    assert run(set_tool, text="gym", at_time="09:00", day="tomorrow") == "Reminder 3 set for Mon 14 Sep 09:00 AM: gym"
    assert run(list_tool) == ("1: stretch at Sun 13 Sep 05:35 PM\n2: call mom at Sun 13 Sep 06:30 PM\n"
                              "3: gym at Mon 14 Sep 09:00 AM")


def test_invalid_reminder_requests(tmp_path) -> None:
    set_tool, list_tool = tools(tmp_path)
    assert run(list_tool) == "No upcoming reminders."
    assert run(set_tool, text="x") == "ERROR: give exactly one of in_minutes or at_time"
    assert run(set_tool, text="x", in_minutes=5, at_time="18:00") == "ERROR: give exactly one of in_minutes or at_time"
    assert run(set_tool, text="x", at_time="25:99") == "ERROR: at_time must be HH:MM, got '25:99'"
    assert run(set_tool, text="x", at_time="09:00") == "ERROR: that time has already passed today; use day='tomorrow'"


def test_reminder_tools_are_registered_with_a_scheduler(tmp_path) -> None:
    settings = Settings(_env_file=None)
    assert "set_reminder" not in build_default_registry(settings).names()
    scheduler = ReminderScheduler(MemoryDB(tmp_path / "m.db"), lambda i, t: None)
    assert {"set_reminder", "list_reminders"} <= set(build_default_registry(settings, scheduler=scheduler).names())