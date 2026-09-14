"""Base class for every tool the model can call."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel


class BaseTool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    Args: ClassVar[type[BaseModel]]
    requires_permission: ClassVar[bool] = False

    def parameters(self) -> dict[str, Any]:
        schema = self.Args.model_json_schema()
        schema.pop("title", None)
        for prop in schema.get("properties", {}).values():
            prop.pop("title", None)
        schema.setdefault("properties", {})
        schema.setdefault("required", [])
        return schema

    def parse_args(self, raw: dict[str, Any] | None) -> BaseModel:
        return self.Args.model_validate(raw)

    def schema(self) -> dict[str, Any]:
        return {"type": "function",
                "function": {"name": self.name, "description": self.description, "parameters": self.parameters()}}

    def permission_summary(self, args: BaseModel) -> str:
        return f"{self.name}({args.model_dump_json()})"

    @abstractmethod
    def run(self, args: BaseModel) -> str:
        """Return a plain-text result. Report failures as text starting with 'ERROR:'; never raise."""