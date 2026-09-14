from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from assistant.config import Settings
from assistant.tools.builtin import build_default_registry
from assistant.tools.builtin.calculator import CalculateArgs, CalculateTool
from assistant.tools.builtin.time_tool import GetTimeTool


@pytest.mark.parametrize(("expression", "expected"), [
    ("17 * 23", "17 * 23 = 391"),
    ("2 ^ 10", "2 ^ 10 = 1024"),
    ("sqrt(16) + 1", "sqrt(16) + 1 = 5"),
    ("7 / 2", "7 / 2 = 3.5"),
    ("-(3 - 5)", "-(3 - 5) = 2"),
    ("round(pi, 2)", "round(pi, 2) = 3.14"),
])
def test_calculate_evaluates_arithmetic(expression: str, expected: str) -> None:
    assert CalculateTool().run(CalculateArgs(expression=expression)) == expected


@pytest.mark.parametrize("expression", [
    "__import__('os').system('echo hi')", "open('secrets.txt')", "(1).__class__", "9 ** 9 ** 9", "x + 1", "lambda: 1",
])
def test_calculate_refuses_anything_but_arithmetic(expression: str) -> None:
    assert CalculateTool().run(CalculateArgs(expression=expression)).startswith("ERROR:")


def test_calculate_division_by_zero() -> None:
    assert CalculateTool().run(CalculateArgs(expression="1 / 0")) == "ERROR: division by zero"


def test_get_time_uses_the_injected_clock_and_zone() -> None:
    fixed = datetime(2026, 9, 13, 17, 5, tzinfo=ZoneInfo("Asia/Kolkata"))
    tool = GetTimeTool(timezone="Asia/Kolkata", now=lambda: fixed)
    assert tool.run(tool.parse_args({})) == "Sunday, 13 September 2026, 05:05 PM (Asia/Kolkata)"


def test_default_registry_has_the_basic_tools() -> None:
    registry = build_default_registry(Settings(_env_file=None))
    assert {"get_time", "calculate"} <= set(registry.names())