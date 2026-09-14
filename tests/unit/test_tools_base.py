import pytest
from pydantic import BaseModel, Field, ValidationError

from assistant.tools.base import BaseTool
from assistant.tools.registry import ToolRegistry


class EchoArgs(BaseModel):
    text: str = Field(description="Text to echo")
    times: int = 1


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo text"
    Args = EchoArgs

    def run(self, args: EchoArgs) -> str:
        return args.text * args.times


class DangerTool(EchoTool):
    name = "danger"
    requires_permission = True


def test_schema_uses_openai_function_format_without_titles() -> None:
    assert EchoTool().schema() == {
        "type": "function",
        "function": {
            "name": "echo",
            "description": "Echo text",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to echo"},
                    "times": {"type": "integer", "default": 1},
                },
                "required": ["text"],
            },
        },
    }


def test_parse_args_validates_input() -> None:
    assert EchoTool().parse_args({"text": "hi", "times": 2}).times == 2
    with pytest.raises(ValidationError):
        EchoTool().parse_args({"times": "many"})
    with pytest.raises(ValidationError):
        EchoTool().parse_args(None)


def test_permission_flag_and_default_summary() -> None:
    tool = DangerTool()
    assert tool.requires_permission is True and EchoTool.requires_permission is False
    assert tool.permission_summary(EchoArgs(text="hi")) == 'danger({"text":"hi","times":1})'


def test_registry_register_get_names_all_and_schemas() -> None:
    registry = ToolRegistry()
    echo, danger = EchoTool(), DangerTool()
    registry.register(echo)
    registry.register(danger)
    assert registry.get("echo") is echo and registry.get("missing") is None
    assert registry.names() == ["echo", "danger"]
    assert registry.all() == [echo, danger]
    assert [s["function"]["name"] for s in registry.schemas()] == ["echo", "danger"]
    assert [s["function"]["name"] for s in registry.schemas(["danger", "unknown"])] == ["danger"]


def test_registry_rejects_duplicates_and_invalid_names() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    with pytest.raises(ValueError, match="duplicate"):
        registry.register(EchoTool())

    class BadName(EchoTool):
        name = "has spaces"

    with pytest.raises(ValueError, match="invalid tool name"):
        registry.register(BadName())