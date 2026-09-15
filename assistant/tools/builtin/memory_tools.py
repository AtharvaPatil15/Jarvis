from __future__ import annotations

from pydantic import BaseModel, Field

from assistant.memory.manager import MemoryManager
from assistant.tools.base import BaseTool


class RememberArgs(BaseModel):
    fact: str = Field(description="Short statement about the user to keep, e.g. 'Favourite colour is teal'")


class RememberTool(BaseTool):
    name = "remember"
    description = "Save a fact about the user to long-term memory when they ask you to remember something."
    Args = RememberArgs

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def run(self, args: RememberArgs) -> str:
        fact_id = self._memory.remember(args.fact)
        return "I already remember that." if fact_id is None else f"Remembered (id {fact_id}): {args.fact}"


class RecallArgs(BaseModel):
    query: str = Field(description="What to look up in long-term memory")


class RecallTool(BaseTool):
    name = "recall"
    description = "Search long-term memory for facts about the user. Each line is '<id>: <fact>'."
    Args = RecallArgs

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def run(self, args: RecallArgs) -> str:
        facts = self._memory.search(args.query, k=5, min_score=0.25)
        return "\n".join(f"{f.id}: {f.text}" for f in facts) if facts else "Nothing relevant is remembered."


class ForgetArgs(BaseModel):
    fact_id: int = Field(description="Id of the fact to delete, as shown by recall")


class ForgetTool(BaseTool):
    name = "forget"
    description = "Delete one remembered fact by id. Call recall first to find the id."
    Args = ForgetArgs
    requires_permission = True

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def run(self, args: ForgetArgs) -> str:
        if self._memory.forget(args.fact_id):
            return f"Forgotten fact {args.fact_id}."
        return f"ERROR: no remembered fact with id {args.fact_id}"
