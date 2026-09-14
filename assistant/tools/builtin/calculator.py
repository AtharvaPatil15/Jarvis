from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from assistant.tools.base import BaseTool

_BINARY: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY: dict[type, Callable[[Any], Any]] = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log, "log10": math.log10,
    "exp": math.exp, "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}
_MAX_EXPONENT = 1000


def evaluate(expression: str) -> int | float:
    return _eval(ast.parse(expression.replace("^", "**"), mode="eval").body)


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError("exponent too large")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS and not node.keywords:
        return _FUNCTIONS[node.func.id](*(_eval(arg) for arg in node.args))
    raise ValueError("only numbers, arithmetic operators and basic maths functions are allowed")


class CalculateArgs(BaseModel):
    expression: str = Field(description="Arithmetic expression, for example '17 * 23' or 'sqrt(2) ^ 3'")


class CalculateTool(BaseTool):
    name = "calculate"
    description = "Evaluate an arithmetic expression exactly. Use for any maths the user asks."
    Args = CalculateArgs

    def run(self, args: CalculateArgs) -> str:
        try:
            value = evaluate(args.expression)
        except ZeroDivisionError:
            return "ERROR: division by zero"
        except (ValueError, TypeError, SyntaxError, OverflowError) as exc:
            return f"ERROR: cannot evaluate {args.expression!r}: {exc}"
        if isinstance(value, float):
            value = int(value) if value.is_integer() and abs(value) < 1e15 else round(value, 10)
        return f"{args.expression} = {value}"