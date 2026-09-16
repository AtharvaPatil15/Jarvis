from pydantic import BaseModel

from assistant.brain.fake_llm import FakeLLM
from assistant.brain.session import Session
from assistant.orchestrator import Orchestrator
from assistant.safety.permissions import AllowAllGate
from assistant.tools.base import BaseTool
from assistant.tools.registry import ToolRegistry
from assistant.tools.selector import ToolSelector


class CountingLLM(FakeLLM):
    def __init__(self) -> None:
        super().__init__()
        self.embedded: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded.extend(texts)
        return super().embed(texts)


def dummy(tool_name: str, text: str) -> BaseTool:
    class Args(BaseModel):
        pass

    return type(f"T_{tool_name}", (BaseTool,), {"name": tool_name, "description": text, "Args": Args,
                                                 "run": lambda self, args: "ok"})()


def big_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(dummy("get_weather", "weather forecast rain temperature wind"))
    registry.register(dummy("recall", "search remembered facts about the user"))
    registry.register(dummy("get_time", "current local date and time"))
    for i, word in enumerate(["piano", "garden", "rocket", "violin", "cooking", "chess", "painting", "hiking",
                              "sailing", "pottery", "juggling", "karate", "origami", "surfing", "knitting"]):
        registry.register(dummy(f"tool_{i}", f"{word} {word} lessons"))
    return registry


def test_small_registries_are_sent_whole_without_embedding() -> None:
    llm = CountingLLM()
    registry = ToolRegistry()
    registry.register(dummy("a", "alpha"))
    registry.register(dummy("b", "beta"))
    assert ToolSelector(llm).select("anything", registry, k=12) == ["a", "b"]
    assert llm.embedded == []


def test_relevant_tools_are_selected_with_always_included_ones_first() -> None:
    llm = CountingLLM()
    chosen = ToolSelector(llm).select("will it rain tomorrow, what is the forecast", big_registry(), k=5)
    assert len(chosen) == 5
    assert chosen[:2] == ["get_time", "recall"]
    assert "get_weather" in chosen


def test_tool_embeddings_are_cached() -> None:
    llm = CountingLLM()
    selector, registry = ToolSelector(llm), big_registry()
    selector.select("rain", registry, k=5)
    first = len(llm.embedded)
    selector.select("chess", registry, k=5)
    assert len(llm.embedded) == first + 1


class ExplodingSelector:
    def select(self, query, registry, k=12):
        raise RuntimeError("embedding model missing")


async def test_selector_failure_falls_back_to_all_tools(events) -> None:
    llm = FakeLLM()
    registry = big_registry()
    orchestrator = Orchestrator(llm, registry, Session(lambda: "SYS"), AllowAllGate(), events, selector=ExplodingSelector())
    assert await orchestrator.handle("hello") == "You said: hello"
    assert len(llm.calls[0]["tools"]) == len(registry.names())