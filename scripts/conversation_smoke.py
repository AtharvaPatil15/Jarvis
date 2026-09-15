"""Hold one WebSocket open, send several utterances, and print a readable transcript."""
from __future__ import annotations

import asyncio
import json
import sys

import websockets

IDLE = {"type": "state_change", "payload": "idle"}


async def run(utterances: list[str], url: str) -> int:
    async with websockets.connect(url, max_size=None) as ws:
        for text in utterances:
            print(f"you> {text}", flush=True)
            await ws.send(json.dumps({"type": "user_text", "payload": text}))
            reply = ""
            while True:
                message = json.loads(await asyncio.wait_for(ws.recv(), timeout=300))
                kind, payload = message["type"], message["payload"]
                if kind == "tool_start":
                    print(f"   tool_start {payload['name']} {json.dumps(payload['arguments'])}", flush=True)
                elif kind == "tool_end":
                    print(f"   tool_end   {payload['name']} ok={payload['ok']} {payload['summary'][:120]!r}", flush=True)
                elif kind == "permission_request":
                    print(f"   permission requested: {payload['summary']}", flush=True)
                elif kind == "error":
                    print(f"   error: {payload['message']}", flush=True)
                elif kind == "ai_response":
                    reply = payload
                elif message == IDLE:
                    break
            print(f"jarvis> {reply}\n", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run(sys.argv[1:] or ["What time is it?"], "ws://127.0.0.1:8000/ws")))