# assistant/brain/llm.py
import json
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("jarvis.llm")
_THINK_BLOCK = re.compile(r" thinking.*? response\s*", re.DOTALL)
_OPEN, _CLOSE = " thinking", " response"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatResult:
    content: str
    tool_calls: list[ToolCall]


class LLMError(RuntimeError):
    """The language model backend failed or returned an unusable response."""


def _partial_suffix(text: str, tag: str) -> int:
    for size in range(min(len(tag) - 1, len(text)), 1, -1):
        if text.endswith(tag[:size]):
            return size
    return 0


class _ThinkFilter:
    """Removes  thinking... response spans from a stream of text chunks, even when tags are split across chunks."""

    def __init__(self) -> None:
        self._buffer = ""
        self._inside = False

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        out: list[str] = []
        while self._buffer:
            if self._inside:
                end = self._buffer.find(_CLOSE)
                if end == -1:
                    self._buffer = self._buffer[-len(_CLOSE):]
                    break
                self._buffer = self._buffer[end + len(_CLOSE):].lstrip()
                self._inside = False
            else:
                start = self._buffer.find(_OPEN)
                if start == -1:
                    keep = _partial_suffix(self._buffer, _OPEN)
                    out.append(self._buffer[: len(self._buffer) - keep])
                    self._buffer = self._buffer[len(self._buffer) - keep:]
                    break
                out.append(self._buffer[:start])
                self._buffer = self._buffer[start + len(_OPEN):]
                self._inside = True
        return "".join(out)

    def flush(self) -> str:
        rest = "" if self._inside else self._buffer
        self._buffer = ""
        return rest


def _parse_tool_calls(raw: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for item in raw or []:
        function = item.get("function") or {}
        name = function.get("name")
        if not name:
            continue
        arguments = function.get("arguments") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError:
                arguments = {"_raw": arguments}
        calls.append(ToolCall(id=item.get("id") or uuid.uuid4().hex[:12], name=name, arguments=arguments))
    return calls


class LLMClient:
    def __init__(self, base_url: str, model: str, embed_model: str, timeout_s: float = 120.0,
                 disable_thinking: bool = True, transport: httpx.BaseTransport | None = None) -> None:
        self.model = model
        self.embed_model = embed_model
        self.disable_thinking = disable_thinking
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_s, transport=transport)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
             temperature: float = 0.4, max_tokens: int = 512,
             on_delta: Callable[[str], None] | None = None) -> ChatResult:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": on_delta is not None,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            body["tools"] = tools
        if self.disable_thinking:
            body["think"] = False
        try:
            if on_delta is not None:
                return self._stream(body, on_delta)
            message = self._checked(self._http.post("/api/chat", json=body)).get("message") or {}
            content = _THINK_BLOCK.sub("", message.get("content") or "").strip()
            return ChatResult(content=content, tool_calls=_parse_tool_calls(message.get("tool_calls")))
        except httpx.TransportError as exc:
            raise LLMError(f"Ollama unreachable at {self._http.base_url}: {exc}") from exc

    def _stream(self, body: dict[str, Any], on_delta: Callable[[str], None]) -> ChatResult:
        think = _ThinkFilter()
        parts: list[str] = []
        calls: list[ToolCall] = []
        with self._http.stream("POST", "/api/chat", json=body) as response:
            if response.status_code != 200:
                response.read()
                raise LLMError(f"Ollama chat failed with HTTP {response.status_code}: {response.text[:300]}")
            for line in response.iter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise LLMError(f"Ollama error: {data['error']}")
                message = data.get("message") or {}
                calls.extend(_parse_tool_calls(message.get("tool_calls")))
                text = think.feed(message.get("content") or "")
                if text:
                    parts.append(text)
                    on_delta(text)
        tail = think.flush()
        if tail:
            parts.append(tail)
            on_delta(tail)
        return ChatResult(content="".join(parts).strip(), tool_calls=calls)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            data = self._checked(self._http.post("/api/embed", json={"model": self.embed_model, "input": texts}))
        except httpx.TransportError as exc:
            raise LLMError(f"Ollama unreachable at {self._http.base_url}: {exc}") from exc
        vectors = data.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise LLMError("Ollama returned an unexpected embedding payload")
        return vectors

    def health(self) -> bool:
        try:
            return self._http.get("/api/tags", timeout=3).status_code == 200
        except httpx.HTTPError:
            return False

    def close(self) -> None:
        self._http.close()

    @staticmethod
    def _checked(response: httpx.Response) -> dict[str, Any]:
        if response.status_code != 200:
            raise LLMError(f"Ollama request failed with HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
        if isinstance(data, dict) and "error" in data:
            raise LLMError(f"Ollama error: {data['error']}")
        return data
