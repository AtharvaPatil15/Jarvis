import pytest

from assistant.memory.redact import redact


@pytest.mark.parametrize(("text", "expected"), [
    ("mail me at atharva.p@example.com please", "mail me at [email] please"),
    ("my number is +91 98765 43210", "my number is [phone]"),
    ("card 4111 1111 1111 1111 expires soon", "card [card] expires soon"),
    ("aadhaar 1234 5678 9012", "aadhaar [id-number]"),
    ("my password is hunter2", "my password is [redacted]"),
    ("PIN: 4821", "PIN: [redacted]"),
])
def test_sensitive_values_are_replaced(text: str, expected: str) -> None:
    assert redact(text) == expected


def test_api_keys_are_replaced() -> None:
    key = "sk-" + "a" * 24
    assert redact(f"use {key} now") == "use [secret] now"


@pytest.mark.parametrize("text", ["meet at 5:30 tomorrow", "the year 2026 was busy", "call me at 10", "room 404"])
def test_ordinary_text_is_untouched(text: str) -> None:
    assert redact(text) == text
