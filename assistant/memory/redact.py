"""Replaces sensitive values before anything is written to disk."""
from __future__ import annotations

import re

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:sk-|gh[pousr]_|AIza)[A-Za-z0-9_-]{16,}\b"), "[secret]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email]"),
    (re.compile(r"\b\d(?:[ -]?\d){12,18}\b"), "[card]"),
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "[id-number]"),
    (re.compile(r"(?<!\w)(?:\+?\d{1,3}[ -]?)?\d(?:[ -]?\d){9,11}(?!\w)"), "[phone]"),
    (re.compile(r"(?i)\b(password|passcode|pin|otp)\b(\s*(?:is|:|=)\s*)\S+"), r"\1\2[redacted]"),
]


def redact(text: str) -> str:
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text
