import json

import httpx
import pytest

from assistant.brain.llm import ChatResult, LLMClient, LLMError

TOOLS = [{"type": "function", "function": {"name": "get_time", "description": "d",
                                           "parameters": {"type": "object", "properties": {}, "required": []}}}]


def make_client(handler, **kwargs) -> LLMClient:
    return LLMClient("http://ollama.test", "qwen3:8b", "nomic-embed-text",
                     transport=httpx.MockTransport(handler), **kwargs)


def ndjson(*objects: dict) -> bytes:
    return "\n".join(json.dumps(o) for o in objects).encode()


def test_chat_sends_native_payload_and_parses_content() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Hello."}, "done": True})

    result = make_client(handler).chat([{"role": "user", "content": "hi"}], temperature=0.2, max_tokens=64)
    assert result == ChatResult(content="Hello.", tool_calls=[])
    assert seen["url"] == "http://ollama.test/api/chat"
    assert seen["body"] == {
        "model": "qwen3:8b",
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.2, "num_predict": 64},
    }


def test_think_flag_is_omitted_when_thinking_is_not_disabled() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "ok"}, "done": True})

    make_client(handler, disable_thinking=False).chat([{"role": "user", "content": "hi"}])
    assert "think" not in seen["body"]


def test_tools_are_sent_and_tool_calls_parsed_with_unique_ids() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "get_time", "arguments": {}}},
            {"function": {"name": "calculate", "arguments": {"expression": "2+2"}}},
        ]}, "done": True})

    result = make_client(handler).chat([{"role": "user", "content": "time?"}], tools=TOOLS)
    assert seen["body"]["tools"] == TOOLS
    assert [c.name for c in result.tool_calls] == ["get_time", "calculate"]
    assert result.tool_calls[1].arguments == {"expression": "2+2"}
    ids = [c.id for c in result.tool_calls]
    assert all(ids) and len(set(ids)) == 2


def test_string_arguments_are_json_decoded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "", "tool_calls": [
            {"function": {"name": "calculate", "arguments": "{\"expression\": \"3*3\"}"}}]}, "done": True})

    assert make_client(handler).chat([{"role": "user", "content": "x"}]).tool_calls[0].arguments == {"expression": "3*3"}


def test_think_blocks_are_stripped_from_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": " thinking\nhmm\n response\n\nThe answer is 4."}, "done": True})

    assert make_client(handler).chat([{"role": "user", "content": "2+2"}]).content == "The answer is 4."


def test_streaming_forwards_deltas_and_aggregates() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=ndjson(
            {"message": {"role": "assistant", "content": "The "}, "done": False},
            {"message": {"content": "answer "}, "done": False},
            {"message": {"content": "is 4."}, "done": True},
        ))

    chunks: list[str] = []
    result = make_client(handler).chat([{"role": "user", "content": "2+2"}], on_delta=chunks.append)
    assert seen["body"]["stream"] is True
    assert chunks == ["The ", "answer ", "is 4."]
    assert result.content == "The answer is 4."


def test_streaming_hides_think_blocks_split_across_chunks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson(
            {"message": {"content": " thi"}, "done": False},
            {"message": {"content": "nking\n response"}, "done": False},
            {"message": {"content": "Hi"}, "done": True},
        ))

    chunks: list[str] = []
    result = make_client(handler).chat([{"role": "user", "content": "x"}], on_delta=chunks.append)
    assert "".join(chunks) == "Hi"
    assert result.content == "Hi"


def test_streaming_collects_tool_calls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=ndjson(
            {"message": {"content": "", "tool_calls": [{"function": {"name": "get_time", "arguments": {}}}]}, "done": False},
            {"message": {"content": ""}, "done": True},
        ))

    chunks: list[str] = []
    result = make_client(handler).chat([{"role": "user", "content": "x"}], tools=TOOLS, on_delta=chunks.append)
    assert [c.name for c in result.tool_calls] == ["get_time"]
    assert chunks == []


def test_http_error_raises_llm_error() -> None:
    client = make_client(lambda request: httpx.Response(500, text="boom"))
    with pytest.raises(LLMError, match="500"):
        client.chat([{"role": "user", "content": "x"}])


def test_error_field_raises_llm_error() -> None:
    client = make_client(lambda request: httpx.Response(200, json={"error": "model 'x' not found"}))
    with pytest.raises(LLMError, match="not found"):
        client.chat([{"role": "user", "content": "x"}])


def test_connection_failure_raises_llm_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(LLMError, match="unreachable"):
        make_client(handler).chat([{"role": "user", "content": "x"}])


def test_embed_posts_inputs_and_returns_vectors() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["body"] = str(request.url), json.loads(request.content)
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    assert make_client(handler).embed(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert seen == {"url": "http://ollama.test/api/embed", "body": {"model": "nomic-embed-text", "input": ["a", "b"]}}


def test_embed_empty_input_makes_no_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    assert make_client(handler).embed([]) == []


def test_embed_wrong_count_raises() -> None:
    client = make_client(lambda request: httpx.Response(200, json={"embeddings": [[0.1]]}))
    with pytest.raises(LLMError):
        client.embed(["a", "b"])


def test_health_reflects_tags_endpoint() -> None:
    assert make_client(lambda request: httpx.Response(200, json={"models": []})).health() is True

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    assert make_client(down).health() is False