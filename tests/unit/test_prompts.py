from datetime import datetime
from zoneinfo import ZoneInfo

from assistant.brain.prompts import build_system_prompt
from assistant.config import Settings

NOW = datetime(2026, 9, 13, 17, 5, tzinfo=ZoneInfo("Asia/Kolkata"))


def test_prompt_contains_time_place_user_and_voice_style() -> None:
    prompt = build_system_prompt(Settings(_env_file=None), NOW)
    assert "Sunday, 13 September 2026, 05:05 PM" in prompt
    assert "Pimpri-Chinchwad, Maharashtra, India" in prompt
    assert "Final-year engineering student" in prompt
    assert "1-2 short sentences" in prompt
    assert "remember" not in prompt.lower()


def test_memories_are_listed_when_given() -> None:
    prompt = build_system_prompt(Settings(_env_file=None), NOW, memories=["Favourite colour is teal", "Owns a cat"])
    assert "- Favourite colour is teal" in prompt
    assert "- Owns a cat" in prompt