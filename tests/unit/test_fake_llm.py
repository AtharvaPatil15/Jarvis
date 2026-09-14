import numpy as np

from assistant.brain.fake_llm import FakeLLM
from assistant.brain.llm import ChatResult, ToolCall


def test_default_reply_echoes_last_user_message() -> None:
    result = FakeLLM().chat([{"role": "system", "content": "x"}, {"role": "user", "content": "hello"}])
    assert result == ChatResult(content="You said: hello", tool_calls=[])


def test_script_is_consumed_in_order_and_calls_are_recorded() -> None:
    call = ToolCall(id="c1", name="get_time", arguments={})
    llm = FakeLLM(script=[ChatResult(content="", tool_calls=[call]), ChatResult(content="done", tool_calls=[])])
    assert llm.chat([{"role": "user", "content": "a"}], tools=[{"type": "function"}]).tool_calls == [call]
    assert llm.chat([{"role": "user", "content": "b"}]).content == "done"
    assert [c["tools"] for c in llm.calls] == [[{"type": "function"}], None]


def test_on_delta_chunks_join_to_the_content() -> None:
    chunks: list[str] = []
    result = FakeLLM().chat([{"role": "user", "content": "stream this please"}], on_delta=chunks.append)
    assert len(chunks) > 1
    assert "".join(chunks) == result.content


def test_legacy_generate_extracts_the_user_line() -> None:
    assert FakeLLM().generate("SYSTEM CONTEXT\n\nUser: what's up\nJarvis:") == "You said: what's up"


def test_embeddings_are_deterministic_normalised_and_similarity_aware() -> None:
    llm = FakeLLM()
    a, b, c = (np.array(v) for v in llm.embed(["my favourite colour is teal", "favourite colour teal", "weather in Pune"]))
    assert np.isclose(np.linalg.norm(a), 1.0)
    assert llm.embed(["same"]) == llm.embed(["same"])
    assert float(a @ b) > float(a @ c)


def test_health_flag() -> None:
    assert FakeLLM().health() is True
    assert FakeLLM(healthy=False).health() is False