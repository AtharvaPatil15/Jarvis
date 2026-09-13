"""Probe the local Ollama models for every capability JARVIS depends on."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

GET_TIME_TOOL = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "Get the current local date and time.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}
SYSTEM = {"role": "system", "content": "You are Jarvis. Call a tool whenever a tool can answer the question."}


def _body(model: str, messages: list[dict[str, Any]], *, think_false: bool, tools: list | None = None,
          stream: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {"temperature": 0, "num_predict": 256},
    }
    if tools:
        body["tools"] = tools
    if think_false:
        body["think"] = False
    return body


def probe(base_url: str, model: str, embed_model: str) -> dict[str, Any]:
    report: dict[str, Any] = {"model": model, "embed_model": embed_model, "checks": {}}
    checks = report["checks"]
    with httpx.Client(base_url=base_url, timeout=300) as client:
        names = {m["name"] for m in client.get("/api/tags").json().get("models", [])}
        has = lambda n: n in names or f"{n}:latest" in names  # noqa: E731
        checks["models_present"] = {"ok": has(model) and has(embed_model), "installed": sorted(names)}

        think_false = True
        start = time.perf_counter()
        ping = [{"role": "user", "content": "Reply with exactly one word: pong"}]
        resp = client.post("/api/chat", json=_body(model, ping, think_false=True))
        if resp.status_code == 400 and "think" in resp.text.lower():
            think_false = False
            resp = client.post("/api/chat", json=_body(model, ping, think_false=False))
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        report["think_false_supported"] = think_false
        checks["plain_chat"] = {
            "ok": "pong" in content.lower() and " thinking" not in content,
            "content": content[:200],
            "seconds": round(time.perf_counter() - start, 2),
        }

        question = [SYSTEM, {"role": "user", "content": "What time is it right now?"}]
        hits, assistant_msg, attempts = 0, None, []
        for _ in range(3):
            start = time.perf_counter()
            msg = client.post(
                "/api/chat", json=_body(model, question, think_false=think_false, tools=[GET_TIME_TOOL])
            ).json()["message"]
            calls = msg.get("tool_calls") or []
            called = [c["function"]["name"] for c in calls]
            attempts.append({"called": called, "seconds": round(time.perf_counter() - start, 2)})
            if "get_time" in called:
                hits += 1
                assistant_msg = msg
        checks["tool_call"] = {"ok": hits >= 2, "hits": hits, "attempts": attempts}

        if assistant_msg is not None:
            follow = question + [
                assistant_msg,
                {"role": "tool", "tool_name": "get_time", "content": "The current local time is 14:05."},
            ]
            final = client.post("/api/chat", json=_body(model, follow, think_false=think_false,
                                                        tools=[GET_TIME_TOOL])).json()["message"]["content"]
            checks["tool_result_round_trip"] = {"ok": "14:05" in final or "2:05" in final, "content": final[:200]}
        else:
            checks["tool_result_round_trip"] = {"ok": False, "content": "no tool call to follow up"}

        chunks = 0
        story = [{"role": "user", "content": "Count from one to ten in words."}]
        with client.stream("POST", "/api/chat", json=_body(model, story, think_false=think_false, stream=True)) as s:
            for line in s.iter_lines():
                if line and json.loads(line).get("message", {}).get("content"):
                    chunks += 1
        checks["streaming"] = {"ok": chunks >= 2, "chunks": chunks}

        emb = client.post("/api/embed", json={"model": embed_model, "input": ["hello world", "goodbye"]}).json()
        vectors = emb.get("embeddings") or []
        report["embedding_dim"] = len(vectors[0]) if vectors else 0
        checks["embeddings"] = {
            "ok": len(vectors) == 2 and len(vectors[0]) == len(vectors[1]) > 0,
            "dim": report["embedding_dim"],
        }
    report["ok"] = all(c["ok"] for c in checks.values())
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("JARVIS_OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--model", default=os.environ.get("JARVIS_CHAT_MODEL", "qwen3:8b"))
    parser.add_argument("--embed-model", default=os.environ.get("JARVIS_EMBED_MODEL", "nomic-embed-text"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    report = probe(args.url, args.model, args.embed_model)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())