from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from assistant.brain.fake_llm import FakeLLM
from assistant.brain.llm import ChatResult, LLMError, ToolCall
from assistant.brain.session import Session
from assistant.orchestrator import APOLOGY, STEP_LIMIT_REPLY, Orchestrator
from assistant.safety.permissions import AllowAllGate, DenyAllGate
from assistant.tools.base import BaseTool
from assistant.tools.builtin.calculator import CalculateTool
from assistant.tools.builtin.time_tool import GetTimeTool
from assistant.tools.registry import ToolRegistry

FIXED = datetime(2026, 9, 13, 17, 5, tzinfo=ZoneInfo("Asia/Kolkata"))
TIME_TEXT = "Sunday, 13 September 2026, 05:05 PM (Asia/Kolkata)"


class DangerTool(BaseTool):
    name = "danger"
    description = "Needs permission"
    requires_permission = True

    class Args(BaseModel):
        target: str

    def __init__(self) -> None:
        self.ran_with: list[str] = []

    def run(self, args) -> str:
        self.ran_with.append(args.target)
        return f"did {args.target}"


class CrashTool(BaseTool):
    name = "crash"
    description = "Always raises"

    class Args(BaseModel):
        pass

    def run(self, args) -> str:
        raise RuntimeError("kaboom")


class BrokenLLM(FakeLLM):
    def chat(self, *args, **kwargs):
        raise LLMError("Ollama unreachable at http://127.0.0.1:11434")


def call(name: str, **arguments) -> ToolCall:
    return ToolCall(id=f"id-{name}", name=name, arguments=arguments)


def tools(*calls: ToolCall) -> ChatResult:
    return ChatResult(content="", tool_calls=list(calls))


def answer(text: str) -> ChatResult:
    return ChatResult(content=text, tool_calls=[])


def make(events, script=(), gate=None, max_steps=5, llm=None):
    registry = ToolRegistry()
    registry.register(GetTimeTool(now=lambda: FIXED))
    registry.register(CalculateTool())
    danger = DangerTool()
    registry.register(danger)
    registry.register(CrashTool())
    llm = llm or FakeLLM(script=list(script))
    orchestrator = Orchestrator(llm, registry, Session(lambda: "SYS"), gate or AllowAllGate(), events,
                                max_steps=max_steps)
    return orchestrator, llm, danger


async def test_plain_answer_streams_and_emits_in_order(events) -> None:
    orchestrator, _, _ = make(events)
    reply = await orchestrator.handle("hi there")
    assert reply == "You said: hi there"
    assert events.events[0] == ("state_change", "thinking")
    assert events.events[1] == ("state_change", "responding")
    assert events.events[-1] == ("ai_response", reply)
    assert "".join(events.payloads("ai_response_delta")) == reply
    assert "idle" not in events.payloads("state_change")


async def test_on_delta_receives_the_stream(events) -> None:
    orchestrator, _, _ = make(events)
    chunks: list[str] = []
    reply = await orchestrator.handle("stream me", on_delta=chunks.append)
    assert "".join(chunks) == reply


async def test_tool_call_result_goes_back_to_the_model(events) -> None:
    orchestrator, llm, _ = make(events, [tools(call("get_time")), answer("It is 5 PM.")])
    assert await orchestrator.handle("what time is it?") == "It is 5 PM."
    assert [s["function"]["name"] for s in llm.calls[0]["tools"]] == ["get_time", "calculate", "danger", "crash"]
    assert llm.calls[1]["messages"][-1] == {"role": "tool", "tool_name": "get_time", "content": TIME_TEXT}
    assert events.events[1] == ("state_change", "executing_tool")
    assert ("tool_start", {"id": "id-get_time", "name": "get_time", "arguments": {}}) in events.events
    end = events.payloads("tool_end")[0]
    assert end["ok"] is True and end["id"] == "id-get_time" and end["summary"].startswith("Sunday")
    types = events.types()
    assert types.index("tool_start") < types.index("tool_end") < types.index("ai_response")


async def test_unknown_tool_is_reported_to_the_model(events) -> None:
    orchestrator, llm, _ = make(events, [tools(call("teleport")), answer("I can't do that.")])
    await orchestrator.handle("teleport me")
    assert llm.calls[1]["messages"][-1]["content"] == "ERROR: unknown tool 'teleport'"
    assert events.payloads("tool_end")[0]["ok"] is False


async def test_invalid_arguments_are_reported(events) -> None:
    orchestrator, llm, _ = make(events, [tools(call("calculate")), answer("Sorry.")])
    await orchestrator.handle("calculate")
    assert llm.calls[1]["messages"][-1]["content"].startswith("ERROR: invalid arguments for calculate")


async def test_permission_denied_blocks_the_tool(events) -> None:
    orchestrator, llm, danger = make(events, [tools(call("danger", target="files")), answer("Okay.")], gate=DenyAllGate())
    await orchestrator.handle("delete files")
    assert danger.ran_with == []
    assert llm.calls[1]["messages"][-1]["content"] == "ERROR: the user denied permission for danger"


async def test_permission_granted_runs_the_tool(events) -> None:
    orchestrator, llm, danger = make(events, [tools(call("danger", target="files")), answer("Done.")])
    await orchestrator.handle("delete files")
    assert danger.ran_with == ["files"]
    assert llm.calls[1]["messages"][-1]["content"] == "did files"


async def test_crashing_tool_is_contained(events) -> None:
    orchestrator, llm, _ = make(events, [tools(call("crash")), answer("That failed.")])
    assert await orchestrator.handle("crash") == "That failed."
    assert llm.calls[1]["messages"][-1]["content"] == "ERROR: crash failed: kaboom"


async def test_step_limit_stops_endless_tool_loops(events) -> None:
    orchestrator, llm, _ = make(events, [tools(call("get_time")) for _ in range(10)], max_steps=3)
    assert await orchestrator.handle("loop") == STEP_LIMIT_REPLY
    assert len(llm.calls) == 3


async def test_llm_failure_emits_error_and_apology(events) -> None:
    orchestrator, _, _ = make(events, llm=BrokenLLM())
    assert await orchestrator.handle("hello") == APOLOGY
    assert events.payloads("error") == [{"message": "Ollama unreachable at http://127.0.0.1:11434"}]
    assert events.events[-2:] == [("state_change", "responding"), ("ai_response", APOLOGY)]


async def test_history_carries_between_turns(events) -> None:
    orchestrator, llm, _ = make(events)
    await orchestrator.handle("my name is Atharva")
    await orchestrator.handle("what is my name?")
    contents = [m["content"] for m in llm.calls[1]["messages"]]
    assert "my name is Atharva" in contents and "You said: my name is Atharva" in contents


async def test_blank_input_does_nothing(events) -> None:
    orchestrator, llm, _ = make(events)
    assert await orchestrator.handle("   ") == ""
    assert events.events == [] and llm.calls == []