"""Send one user_text command to a running backend and print every event until the state returns to idle."""
from __future__ import annotations

import asyncio
import json
import sys

import websockets

IDLE = {"type": "state_change", "payload": "idle"}


async def run(text: str, url: str, timeout_s: float) -> int:
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"type": "user_text", "payload": text}))
        while True:
            message = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout_s))
            print(json.dumps(message), flush=True)
            if message == IDLE:
                return 0


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "hello jarvis"
    url = sys.argv[2] if len(sys.argv) > 2 else "ws://127.0.0.1:8000/ws"
    sys.exit(asyncio.run(run(text, url, timeout_s=180)))