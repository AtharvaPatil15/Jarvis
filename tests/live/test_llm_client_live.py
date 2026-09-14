import numpy as np
import pytest

from assistant.brain.llm import LLMClient
from assistant.config import Settings

pytestmark = pytest.mark.live
GET_TIME = {"type": "function", "function": {"name": "get_time", "description": "Get the current local time.",
                                             "parameters": {"type": "object", "properties": {}, "required": []}}}


@pytest.fixture(scope="module")
def client() -> LLMClient:
    s = Settings(_env_file=None)
    c = LLMClient(s.ollama_url, s.chat_model, s.embed_model, s.llm_timeout_s, s.llm_disable_thinking)
    yield c
    c.close()


def test_plain_chat(client: LLMClient) -> None:
    result = client.chat([{"role": "user", "content": "Reply with exactly one word: pong"}], temperature=0)
    assert "pong" in result.content.lower()
    assert " thinking" not in result.content


def test_tool_call_is_chosen(client: LLMClient) -> None:
    messages = [{"role": "system", "content": "Use tools whenever they can answer."},
                {"role": "user", "content": "What time is it right now?"}]
    hits = sum("get_time" in [c.name for c in client.chat(messages, tools=[GET_TIME], temperature=0).tool_calls]
               for _ in range(3))
    assert hits >= 2


def test_streaming_matches_content(client: LLMClient) -> None:
    chunks: list[str] = []
    result = client.chat([{"role": "user", "content": "Count from one to five in words."}], on_delta=chunks.append)
    assert len(chunks) >= 2
    assert "".join(chunks).strip() == result.content


def test_embeddings_capture_similarity(client: LLMClient) -> None:
    a, b, c = (np.array(v) for v in client.embed(["my favourite colour is teal", "I like the colour teal",
                                                  "the stock market fell today"]))
    cos = lambda x, y: float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y)))  # noqa: E731
    assert cos(a, b) > cos(a, c)