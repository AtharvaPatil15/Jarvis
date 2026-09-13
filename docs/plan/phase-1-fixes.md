# Phase 1 — Fix what is broken and make the backend testable

Order: **P1-T1 → P1-T2 → P1-T3**. After P1-T3: full gate, then `git push origin testing`.

---

## P1-T1: Server app factory, ordered event hub, crash fix, `FakeLLM`

**Goal:** `server.py` no longer builds anything at import time, no longer crashes after a reply, starts without
voice hardware, and can be tested with a deterministic fake model.

**Depends on:** P0-T4.

**Files:**
- Create: `assistant/hub.py`, `assistant/brain/fake_llm.py`, `scripts/backend.ps1`, `tests/unit/test_hub.py`,
  `tests/unit/test_fake_llm.py`, `tests/unit/test_server_app.py`, `tests/unit/test_legacy_voice.py`, `docs/proof/P1-T1.md`
- Modify: `server.py` (rewrite), `start_backend.py` (rewrite), `assistant/brain/llm.py` (add types + `health`),
  `assistant/orchestrator.py` (inject `llm`), `assistant/voice/voice_controller.py` (add `conv_manager`)

**Interfaces**
- Consumes: `Settings`, `get_settings` (P0-T4); `EventType`, `AssistantState` (P0-T4).
- Produces: `ConnectionHub` (PLAN §3.10 incl. `bind_loop`, `close`, `drain`, `client_count`, `loop`);
  `ToolCall`, `ChatResult`, `LLMError` in `assistant/brain/llm.py`; `FakeLLM` with `chat`, `embed`, `health`, and a
  temporary `generate(prompt) -> str` (removed in P2-T6); `server.create_app(settings=None, *, llm=None, enable_voice=None)`;
  `server.mark_voice_idle(voice) -> None`; `app.state.hub`, `app.state.llm`, `app.state.voice`, `app.state.settings`,
  `app.state.process_text`; `scripts/backend.ps1 -Start [-Fake] [-NoVoice] [-Port] [-TimeoutSec] | -Stop`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_hub.py`:
```python
import asyncio

from assistant.events import AssistantState, EventType
from assistant.hub import ConnectionHub


class FakeSocket:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[dict] = []
        self.accepted = False
        self.fail = fail

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        if self.fail:
            raise RuntimeError("socket closed")
        self.sent.append(data)


async def _hub_with(*sockets: FakeSocket) -> ConnectionHub:
    hub = ConnectionHub()
    hub.bind_loop(asyncio.get_running_loop())
    for socket in sockets:
        await hub.connect(socket)
    return hub


async def test_messages_arrive_in_emit_order() -> None:
    ws = FakeSocket()
    hub = await _hub_with(ws)
    for i in range(25):
        hub.emit("state_change", str(i))
    await hub.drain()
    assert [m["payload"] for m in ws.sent] == [str(i) for i in range(25)]
    assert ws.accepted
    await hub.close()


async def test_emit_from_another_thread_is_delivered() -> None:
    ws = FakeSocket()
    hub = await _hub_with(ws)
    await asyncio.to_thread(hub.emit, "user_transcript", "hi")
    await hub.drain()
    assert ws.sent == [{"type": "user_transcript", "payload": "hi"}]
    await hub.close()


async def test_failing_socket_is_dropped_and_others_still_receive() -> None:
    good, bad = FakeSocket(), FakeSocket(fail=True)
    hub = await _hub_with(good, bad)
    await hub.broadcast("error", {"message": "x"})
    await hub.drain()
    assert hub.client_count == 1
    assert good.sent == [{"type": "error", "payload": {"message": "x"}}]
    await hub.close()


async def test_enums_are_sent_as_plain_strings() -> None:
    ws = FakeSocket()
    hub = await _hub_with(ws)
    hub.emit(EventType.STATE_CHANGE, AssistantState.THINKING)
    await hub.drain()
    assert ws.sent == [{"type": "state_change", "payload": "thinking"}]
    assert type(ws.sent[0]["type"]) is str and type(ws.sent[0]["payload"]) is str
    await hub.close()
```

`tests/unit/test_fake_llm.py`:
```python
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
```

`tests/unit/test_server_app.py`:
```python
import importlib
import sys
import threading
import types

import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from tests.helpers import wait_until

pytestmark = pytest.mark.timeout(30)


def fake_settings(**overrides) -> Settings:
    values = {"llm_backend": "fake", "voice_enabled": False} | overrides
    return Settings(_env_file=None, **values)


def test_importing_server_builds_nothing() -> None:
    module = importlib.reload(server)
    for name in ("app", "voice", "orchestrator", "active_socket"):
        assert not hasattr(module, name), name


def test_health_with_fake_llm_and_voice_disabled() -> None:
    with TestClient(server.create_app(fake_settings())) as client:
        assert client.get("/health").json() == {"status": "ok", "llm": True, "voice": False}


def test_websocket_connect_and_disconnect_are_tracked() -> None:
    app = server.create_app(fake_settings())
    with TestClient(app) as client:
        with client.websocket_connect("/ws"):
            wait_until(lambda: app.state.hub.client_count == 1)
        wait_until(lambda: app.state.hub.client_count == 0)


def test_emit_from_background_thread_reaches_websocket() -> None:
    app = server.create_app(fake_settings())
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        wait_until(lambda: app.state.hub.client_count == 1)
        worker = threading.Thread(target=app.state.hub.emit, args=("state_change", "idle"))
        worker.start()
        worker.join()
        assert ws.receive_json() == {"type": "state_change", "payload": "idle"}


def test_mark_voice_idle_tolerates_missing_manager_and_resets_flag() -> None:
    server.mark_voice_idle(object())

    class Manager:
        is_processing = True

    class Voice:
        conv_manager = Manager()

    voice = Voice()
    server.mark_voice_idle(voice)
    assert voice.conv_manager.is_processing is False


def test_voice_failure_at_startup_does_not_crash_server(monkeypatch) -> None:
    broken = types.ModuleType("assistant.voice.voice_controller")

    class Exploding:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("no microphone")

    broken.VoiceController = Exploding
    monkeypatch.setitem(sys.modules, "assistant.voice.voice_controller", broken)
    with TestClient(server.create_app(fake_settings(voice_enabled=True))) as client:
        assert client.get("/health").json()["voice"] is False
```

`tests/unit/test_legacy_voice.py`:
```python
import importlib
import sys
import types


def _stub_module(monkeypatch, module_name: str, class_name: str) -> None:
    module = types.ModuleType(module_name)
    setattr(module, class_name, type(class_name, (), {"__init__": lambda self, *a, **k: None}))
    monkeypatch.setitem(sys.modules, module_name, module)


def test_legacy_voice_controller_exposes_conv_manager(monkeypatch) -> None:
    import assistant.voice  # noqa: F401  (real package, stubbed submodules below)

    _stub_module(monkeypatch, "assistant.voice.stt", "SpeechToText")
    _stub_module(monkeypatch, "assistant.voice.wake_word", "WakeWordEngine")
    _stub_module(monkeypatch, "assistant.voice.tts", "TextToSpeech")
    monkeypatch.delitem(sys.modules, "assistant.voice.voice_controller", raising=False)
    controller_module = importlib.import_module("assistant.voice.voice_controller")
    controller = controller_module.VoiceController(on_event=lambda *_: None)
    assert controller.conv_manager.is_processing is False
```

Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_hub.py tests/unit/test_fake_llm.py tests/unit/test_server_app.py tests/unit/test_legacy_voice.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'assistant.hub'` (and similar).

- [ ] **Step 2: Add the shared LLM types to `assistant/brain/llm.py`**

Keep `LocalLLM` for now (replaced in P2-T1). Add at the top of the file, below `import requests`:
```python
from dataclasses import dataclass
from typing import Any


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
```
Add this method to `LocalLLM`:
```python
    def health(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/api/tags", timeout=2).status_code == 200
        except requests.RequestException:
            return False
```

- [ ] **Step 3: Write `assistant/brain/fake_llm.py`**

```python
"""Deterministic stand-in for LLMClient: tests, e2e runs and JARVIS_LLM_BACKEND=fake."""
from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from assistant.brain.llm import ChatResult


class FakeLLM:
    def __init__(self, script: Sequence[ChatResult] = (), healthy: bool = True, dim: int = 64) -> None:
        self.script: list[ChatResult] = list(script)
        self.calls: list[dict[str, Any]] = []
        self.healthy = healthy
        self.dim = dim

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.4,
        max_tokens: int = 512,
        on_delta: Callable[[str], None] | None = None,
    ) -> ChatResult:
        self.calls.append({"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)})
        if self.script:
            result = self.script.pop(0)
        else:
            last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
            result = ChatResult(content=f"You said: {last_user}", tool_calls=[])
        if on_delta is not None and result.content:
            for chunk in re.findall(r"\S+\s*", result.content):
                on_delta(chunk)
        return result

    def generate(self, prompt: str) -> str:
        """Legacy LocalLLM-compatible API used by the old orchestrator. Removed in P2-T6."""
        user_lines = [line for line in prompt.splitlines() if line.startswith("User:")]
        text = user_lines[-1][len("User:"):].strip() if user_lines else prompt.strip()
        return f"You said: {text}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = np.zeros(self.dim, dtype=np.float32)
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                vector[int.from_bytes(digest[:4], "little") % self.dim] += 1.0
            norm = float(np.linalg.norm(vector))
            vectors.append((vector / norm if norm else vector).tolist())
        return vectors

    def health(self) -> bool:
        return self.healthy
```

- [ ] **Step 4: Write `assistant/hub.py`**

```python
"""Fan-out of server events to every connected WebSocket, in strict FIFO order, callable from any thread."""
from __future__ import annotations

import asyncio
import contextlib
from enum import Enum
from typing import Any

from fastapi import WebSocket


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


class ConnectionHub:
    def __init__(self) -> None:
        self._clients: set[Any] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[dict[str, Any]] | None = None
        self._pump_task: asyncio.Task[None] | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._queue = asyncio.Queue()
        self._pump_task = loop.create_task(self._pump())

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("ConnectionHub.bind_loop() has not been called")
        return self._loop

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, type_: str, payload: Any) -> None:
        assert self._queue is not None
        self._queue.put_nowait(self._message(type_, payload))

    def emit(self, type_: str, payload: Any) -> None:
        assert self._queue is not None
        self.loop.call_soon_threadsafe(self._queue.put_nowait, self._message(type_, payload))

    async def drain(self) -> None:
        assert self._queue is not None
        await asyncio.sleep(0)
        await self._queue.join()

    async def close(self) -> None:
        if self._pump_task is not None:
            self._pump_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pump_task
            self._pump_task = None

    @staticmethod
    def _message(type_: str, payload: Any) -> dict[str, Any]:
        return {"type": str(_plain(type_)), "payload": _plain(payload)}

    async def _pump(self) -> None:
        assert self._queue is not None
        while True:
            message = await self._queue.get()
            try:
                for ws in list(self._clients):
                    try:
                        await ws.send_json(message)
                    except Exception:
                        self._clients.discard(ws)
            finally:
                self._queue.task_done()
```

- [ ] **Step 5: Inject the LLM into the legacy orchestrator and fix the voice controller**

`assistant/orchestrator.py` — change the constructor to:
```python
    def __init__(self, llm=None):
        self.llm = llm if llm is not None else LocalLLM()
        self.planner = Planner(self.llm)
        self.memory = MemoryStore()
        self.search_tool = SmartSearchTool()
        self.user_profile = self.memory
```
`assistant/voice/voice_controller.py` — add `from .conversation_manager import ConversationManager`, set
`self.conv_manager = ConversationManager()` in `__init__`, and in `_loop` set
`self.conv_manager.is_processing = True` immediately before `self.on_event("process_command", command)`.

- [ ] **Step 6: Rewrite `server.py`**

```python
"""JARVIS backend. Run: .venv/Scripts/python.exe -m uvicorn server:create_app --factory --host 127.0.0.1 --port 8000"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from assistant.config import Settings, get_settings
from assistant.events import EventType
from assistant.hub import ConnectionHub

log = logging.getLogger("jarvis.server")


def build_llm(settings: Settings) -> Any:
    if settings.llm_backend == "fake":
        from assistant.brain.fake_llm import FakeLLM

        return FakeLLM()
    from assistant.brain.llm import LocalLLM

    return LocalLLM(base_url=settings.ollama_url, model=settings.chat_model)


def mark_voice_idle(voice: Any) -> None:
    manager = getattr(voice, "conv_manager", None)
    if manager is not None:
        manager.is_processing = False


def create_app(settings: Settings | None = None, *, llm: Any | None = None,
               enable_voice: bool | None = None) -> FastAPI:
    settings = settings or get_settings()
    voice_wanted = settings.voice_enabled if enable_voice is None else enable_voice
    hub = ConnectionHub()
    llm = llm if llm is not None else build_llm(settings)

    from assistant.orchestrator import Orchestrator

    orchestrator = Orchestrator(llm=llm)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hub.bind_loop(asyncio.get_running_loop())
        if voice_wanted:
            try:
                from assistant.voice.voice_controller import VoiceController

                voice = VoiceController(on_event=on_voice_event)
                voice.start()
                app.state.voice = voice
            except Exception:
                log.exception("voice disabled: voice controller failed to start")
                app.state.voice = None
        try:
            yield
        finally:
            if app.state.voice is not None:
                app.state.voice.stop()
            await hub.close()

    app = FastAPI(title="JARVIS", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.hub = hub
    app.state.settings = settings
    app.state.llm = llm
    app.state.voice = None

    async def process_text(text: str) -> str:
        reply = await asyncio.to_thread(orchestrator.handle_input, text)
        hub.emit(EventType.AI_RESPONSE, reply)
        voice = app.state.voice
        if voice is not None:
            await asyncio.to_thread(voice.speak, reply)
            mark_voice_idle(voice)
        return reply

    app.state.process_text = process_text

    def on_voice_event(event_type: str, data: Any) -> None:
        if event_type in ("process_command", "merge_command"):
            asyncio.run_coroutine_threadsafe(app.state.process_text(str(data)), hub.loop)
            return
        hub.emit(event_type, data)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        check = getattr(app.state.llm, "health", None)
        llm_ok = bool(await asyncio.to_thread(check)) if callable(check) else False
        return {"status": "ok", "llm": llm_ok, "voice": app.state.voice is not None}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await hub.connect(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            hub.disconnect(ws)

    return app
```

- [ ] **Step 7: Rewrite `start_backend.py`**

```python
"""Start the JARVIS backend with settings from assistant/config.py."""
import uvicorn

from assistant.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("server:create_app", factory=True, host=settings.server_host, port=settings.server_port)
```

- [ ] **Step 8: Write `scripts/backend.ps1` (background server helper used by every later proof)**

```powershell
param([switch]$Start, [switch]$Stop, [switch]$Fake, [switch]$NoVoice, [int]$Port = 8000, [int]$TimeoutSec = 120)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force -Path 'docs/proof/tmp' | Out-Null
$pidFile = 'docs/proof/tmp/backend.pid'

if ($Stop) {
    if (Test-Path $pidFile) {
        $procId = [int](Get-Content $pidFile)
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Remove-Item $pidFile
        Write-Output "backend stopped (pid $procId)"
    } else {
        Write-Output 'backend not running'
    }
    exit 0
}

if ($Start) {
    if ($Fake) { $env:JARVIS_LLM_BACKEND = 'fake' } else { Remove-Item Env:JARVIS_LLM_BACKEND -ErrorAction SilentlyContinue }
    if ($NoVoice) { $env:JARVIS_VOICE_ENABLED = 'false' } else { Remove-Item Env:JARVIS_VOICE_ENABLED -ErrorAction SilentlyContinue }
    $proc = Start-Process -FilePath '.venv/Scripts/python.exe' `
        -ArgumentList @('-m', 'uvicorn', 'server:create_app', '--factory', '--host', '127.0.0.1', '--port', "$Port") `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput 'docs/proof/tmp/backend.out.log' -RedirectStandardError 'docs/proof/tmp/backend.err.log'
    Set-Content -Path $pidFile -Value $proc.Id
    for ($i = 0; $i -lt ($TimeoutSec * 2); $i++) {
        if ($proc.HasExited) {
            Write-Output 'backend exited early'
            Get-Content 'docs/proof/tmp/backend.err.log' -Tail 40
            exit 1
        }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
            Write-Output ($health | ConvertTo-Json -Compress)
            exit 0
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    Write-Output "backend not healthy within $TimeoutSec s"
    Get-Content 'docs/proof/tmp/backend.err.log' -Tail 40
    exit 1
}

Write-Output 'usage: backend.ps1 -Start [-Fake] [-NoVoice] [-Port 8000] [-TimeoutSec 120] | -Stop'
exit 2
```

- [ ] **Step 9: Run tests and a real server smoke check**

```powershell
.venv/Scripts/python.exe -m pytest tests/unit -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Start -Fake -NoVoice
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Stop
```
Expected: all unit tests pass; `-Start` prints `{"status":"ok","llm":true,"voice":false}`; `-Stop` prints `backend stopped (pid …)`.

- [ ] **Step 10: Gate, proof, progress, commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add server.py start_backend.py assistant/hub.py assistant/brain/fake_llm.py assistant/brain/llm.py assistant/orchestrator.py assistant/voice/voice_controller.py scripts/backend.ps1 tests/unit/test_hub.py tests/unit/test_fake_llm.py tests/unit/test_server_app.py tests/unit/test_legacy_voice.py docs/proof/P0-T4.md docs/proof/P1-T1.md docs/PROGRESS.md
git commit -m "fix(server): app factory, ordered event hub and conv_manager crash fix [P1-T1]" -m "Proof: docs/proof/P1-T1.md"
```

**Acceptance criteria**
- Importing `server` creates no app, orchestrator, or voice objects.
- `/health` works with voice disabled or failing.
- Events emitted from any thread reach clients in order.

---

## P1-T2: `voice_main.py` crash, Porcupine key via settings, dependency guard tests

**Goal:** The CLI voice entry point calls methods that exist, the legacy wake word reads its key from `Settings` and
fails with a clear message when it is absent, and regressions (key in git, wrong search package) are caught by tests.

**Depends on:** P1-T1.

**Files:**
- Create: `tests/unit/test_legacy_fixes.py`, `docs/proof/P1-T2.md`
- Modify: `voice_main.py`, `assistant/voice/wake_word.py`

- [ ] **Step 1: Write the tests**

`tests/unit/test_legacy_fixes.py`:
```python
import ast
import importlib
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KEY_PREFIX = "ycGaIQ" + "bL2ZWI8r2M"


def _class_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    return {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}


def test_voice_main_only_calls_methods_that_exist_on_speech_to_text() -> None:
    tree = ast.parse((ROOT / "voice_main.py").read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "stt"
    }
    assert called, "voice_main.py should call methods on its SpeechToText instance"
    assert called <= _class_methods(ROOT / "assistant/voice/stt.py", "SpeechToText")


def test_no_porcupine_key_in_any_tracked_file() -> None:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    offenders = [
        name for name in tracked.splitlines()
        if (ROOT / name).is_file() and KEY_PREFIX in (ROOT / name).read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []


def test_smart_search_module_imports() -> None:
    module = importlib.import_module("assistant.tools.smart_search")
    assert module.SmartSearchTool.name == "smart_search"


def test_requirements_use_ddgs_package() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "ddgs" in requirements
    assert "duckduckgo-search" not in requirements


def test_legacy_wake_engine_without_key_fails_clearly(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JARVIS_PORCUPINE_ACCESS_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "pvporcupine", types.ModuleType("pvporcupine"))
    monkeypatch.setitem(sys.modules, "sounddevice", types.ModuleType("sounddevice"))
    monkeypatch.delitem(sys.modules, "assistant.voice.wake_word", raising=False)
    wake_word = importlib.import_module("assistant.voice.wake_word")
    with pytest.raises(RuntimeError, match="JARVIS_PORCUPINE_ACCESS_KEY"):
        wake_word.WakeWordEngine()
```
Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_legacy_fixes.py -q`
Expected: FAIL on `test_voice_main_only_calls_methods_that_exist_on_speech_to_text` (`{'listen'}` is not a subset)
and `test_legacy_wake_engine_without_key_fails_clearly` (no RuntimeError). The key and ddgs tests are regression
guards and already pass.

- [ ] **Step 2: Fix `assistant/voice/wake_word.py`**

Remove the `import os` added in P0-T1 and replace `WakeWordEngine` with:
```python
from assistant.config import get_settings


class WakeWordEngine:
    def __init__(self):
        key = get_settings().porcupine_access_key
        if not key:
            raise RuntimeError(
                "Legacy Porcupine wake word needs JARVIS_PORCUPINE_ACCESS_KEY; it is replaced by openWakeWord in P3."
            )
        self.listener = WakeWordListener(access_key=key, keyword="computer")

    def wait_for_wake(self):
        return self.listener.listen()
```

- [ ] **Step 3: Fix `voice_main.py`**

Remove `import os` and the module-level `PORCUPINE_ACCESS_KEY` line. Add `from assistant.config import get_settings`.
Inside `main()` use `access_key=get_settings().porcupine_access_key` when building `WakeWordListener`, and replace
`command = stt.listen(duration=8)` with:
```python
                command = stt.listen_until_silence()
```

- [ ] **Step 4: Run tests, gate, proof, commit**

```powershell
.venv/Scripts/python.exe -m pytest tests/unit -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add voice_main.py assistant/voice/wake_word.py tests/unit/test_legacy_fixes.py docs/proof/P1-T2.md docs/PROGRESS.md
git commit -m "fix(voice): voice_main STT call and wake word key from settings [P1-T2]" -m "Proof: docs/proof/P1-T2.md"
```

**Acceptance criteria:** all five tests pass; `Select-String -Path voice_main.py -Pattern 'stt\.listen\('` finds nothing.

---

## P1-T3: Text commands over WebSocket, state events, UI event mapping, Electron preload

**Goal:** The UI (and tests) can send `user_text`; the backend emits the full ordered state sequence so the orb
moves through thinking → responding → idle; the UI maps every protocol event through one tested function; the
Electron preload file exists.

**Depends on:** P1-T1.

**Files:**
- Create: `lib/socketEvents.ts`, `lib/socketEvents.test.ts`, `vitest.config.ts`, `electron/preload.js`,
  `scripts/ws_smoke.py`, `tests/unit/test_ws_protocol.py`, `tests/unit/test_electron_files.py`, `docs/proof/P1-T3.md`
- Modify: `server.py` (`process_text`, WebSocket loop), `hooks/useSocket.ts`, `package.json` (vitest + `test` script)

**Interfaces**
- Produces (TS): `ASSISTANT_STATUSES`, `isAssistantStatus(value): value is AssistantStatus`,
  `interface SocketActions { setStatus; setTranscript; setActiveTool }`, `interface ServerEvent { type: string; payload: unknown }`,
  `applyServerEvent(event: ServerEvent, actions: SocketActions): boolean`.
- Produces (Python): WebSocket accepts `user_text`; `app.state.process_text(text) -> str` emits the sequence below.

- [ ] **Step 1: Write the failing Python tests**

`tests/unit/test_ws_protocol.py`:
```python
import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings

pytestmark = pytest.mark.timeout(30)
IDLE = {"type": "state_change", "payload": "idle"}


def fake_app():
    return server.create_app(Settings(_env_file=None, llm_backend="fake", voice_enabled=False))


def receive_until_idle(ws, limit: int = 20) -> list[dict]:
    received = []
    for _ in range(limit):
        message = ws.receive_json()
        received.append(message)
        if message == IDLE:
            return received
    raise AssertionError(f"no idle within {limit} messages: {received}")


def test_user_text_produces_the_ordered_event_sequence() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "hello jarvis"})
        assert receive_until_idle(ws) == [
            {"type": "user_transcript", "payload": "hello jarvis"},
            {"type": "state_change", "payload": "thinking"},
            {"type": "state_change", "payload": "responding"},
            {"type": "ai_response", "payload": "You said: hello jarvis"},
            IDLE,
        ]


def test_blank_text_is_ignored() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "   "})
        ws.send_json({"type": "user_text", "payload": "ping"})
        assert ws.receive_json() == {"type": "user_transcript", "payload": "ping"}


def test_invalid_json_reports_error_and_socket_survives() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_text("not json")
        assert ws.receive_json() == {
            "type": "error", "payload": {"message": "invalid message: expected JSON {type, payload}"}
        }
        ws.send_json({"type": "user_text", "payload": "still alive"})
        assert receive_until_idle(ws)[-2] == {"type": "ai_response", "payload": "You said: still alive"}


def test_unsupported_message_type_reports_error() -> None:
    with TestClient(fake_app()) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "dance", "payload": None})
        assert ws.receive_json() == {"type": "error", "payload": {"message": "unsupported message type: dance"}}


def test_model_failure_emits_error_then_idle(monkeypatch) -> None:
    app = fake_app()

    def boom(prompt: str) -> str:
        raise RuntimeError("model offline")

    monkeypatch.setattr(app.state.llm, "generate", boom)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text", "payload": "anything"})
        assert receive_until_idle(ws) == [
            {"type": "user_transcript", "payload": "anything"},
            {"type": "state_change", "payload": "thinking"},
            {"type": "error", "payload": {"message": "model offline"}},
            IDLE,
        ]
```

`tests/unit/test_electron_files.py`:
```python
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_preload_script_referenced_by_electron_main_exists() -> None:
    main_js = (ROOT / "electron" / "main.js").read_text(encoding="utf-8")
    match = re.search(r"path\.join\(__dirname,\s*[\"']([^\"']+)[\"']\)", main_js)
    assert match, "electron/main.js must reference a preload script"
    assert (ROOT / "electron" / match.group(1)).is_file()
```
Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_ws_protocol.py tests/unit/test_electron_files.py -q`
Expected: FAIL — the WebSocket ignores `user_text` (receive blocks → timeout), `preload.js` missing.

- [ ] **Step 2: Replace `process_text` and the WebSocket loop in `server.py`**

Add `import json` and `from assistant.events import AssistantState, EventType`. Replace the `process_text` function:
```python
    lock = asyncio.Lock()

    async def process_text(text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        async with lock:
            hub.emit(EventType.USER_TRANSCRIPT, text)
            hub.emit(EventType.STATE_CHANGE, AssistantState.THINKING)
            try:
                reply = await asyncio.to_thread(orchestrator.handle_input, text)
            except Exception as exc:
                log.exception("command failed")
                hub.emit(EventType.ERROR, {"message": str(exc)})
                hub.emit(EventType.STATE_CHANGE, AssistantState.IDLE)
                return ""
            hub.emit(EventType.STATE_CHANGE, AssistantState.RESPONDING)
            hub.emit(EventType.AI_RESPONSE, reply)
            voice = app.state.voice
            if voice is not None:
                await asyncio.to_thread(voice.speak, reply)
                mark_voice_idle(voice)
            hub.emit(EventType.STATE_CHANGE, AssistantState.IDLE)
            return reply
```
Replace the body of `websocket_endpoint`:
```python
        await hub.connect(ws)
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    message = json.loads(raw)
                    kind, payload = message["type"], message.get("payload")
                except (ValueError, KeyError, TypeError):
                    hub.emit(EventType.ERROR, {"message": "invalid message: expected JSON {type, payload}"})
                    continue
                if kind == "user_text" and isinstance(payload, str):
                    asyncio.create_task(app.state.process_text(payload))
                else:
                    hub.emit(EventType.ERROR, {"message": f"unsupported message type: {kind}"})
        except WebSocketDisconnect:
            pass
        finally:
            hub.disconnect(ws)
```
Also in `on_voice_event`, emit `hub.emit(EventType.STATE_CHANGE, AssistantState.LISTENING)` right after forwarding
`wake_word_detected`.

- [ ] **Step 3: Write `electron/preload.js`** (same as `git show origin/Test:apps/desktop/preload.js`)

```js
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("jarvisDesktop", {
  platform: process.platform,
});
```
Run the Python tests again. Expected: all pass.

- [ ] **Step 4: Add vitest and write the failing TypeScript test**

```powershell
npm install -D vitest
```
Add `"test": "vitest run"` to `package.json` scripts.

`vitest.config.ts`:
```ts
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['lib/**/*.test.ts', 'store/**/*.test.ts'],
    environment: 'node',
  },
  resolve: {
    alias: { '@': fileURLToPath(new URL('.', import.meta.url)) },
  },
});
```

`lib/socketEvents.test.ts`:
```ts
import { describe, expect, it, vi } from 'vitest';
import { applyServerEvent, isAssistantStatus, type SocketActions } from './socketEvents';

function makeActions(): SocketActions {
  return { setStatus: vi.fn(), setTranscript: vi.fn(), setActiveTool: vi.fn() };
}

describe('applyServerEvent', () => {
  it('sets a valid status from state_change', () => {
    const actions = makeActions();
    expect(applyServerEvent({ type: 'state_change', payload: 'thinking' }, actions)).toBe(true);
    expect(actions.setStatus).toHaveBeenCalledWith('thinking');
  });

  it('rejects an unknown status', () => {
    const actions = makeActions();
    expect(applyServerEvent({ type: 'state_change', payload: 'dancing' }, actions)).toBe(false);
    expect(actions.setStatus).not.toHaveBeenCalled();
  });

  it('switches to listening on wake word', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'wake_word_detected', payload: null }, actions);
    expect(actions.setStatus).toHaveBeenCalledWith('listening');
  });

  it('quotes the user transcript and shows the ai response', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'user_transcript', payload: 'hello' }, actions);
    applyServerEvent({ type: 'ai_response', payload: 'Hi there.' }, actions);
    expect(actions.setTranscript).toHaveBeenNthCalledWith(1, '"hello"');
    expect(actions.setTranscript).toHaveBeenNthCalledWith(2, 'Hi there.');
  });

  it('tracks the active tool from tool_start and clears it on tool_end', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'tool_start', payload: { id: '1', name: 'get_time', arguments: {} } }, actions);
    applyServerEvent({ type: 'tool_end', payload: { id: '1', name: 'get_time', ok: true, summary: '' } }, actions);
    expect(actions.setActiveTool).toHaveBeenNthCalledWith(1, 'get_time');
    expect(actions.setActiveTool).toHaveBeenNthCalledWith(2, null);
  });

  it('shows server errors in the transcript', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'error', payload: { message: 'model offline' } }, actions);
    expect(actions.setTranscript).toHaveBeenCalledWith('Error: model offline');
  });

  it('ignores unknown event types', () => {
    expect(applyServerEvent({ type: 'mystery', payload: 1 }, makeActions())).toBe(false);
  });
});

describe('isAssistantStatus', () => {
  it('accepts exactly the five backend states', () => {
    for (const s of ['idle', 'listening', 'thinking', 'responding', 'executing_tool']) {
      expect(isAssistantStatus(s)).toBe(true);
    }
    expect(isAssistantStatus('speaking')).toBe(false);
    expect(isAssistantStatus(3)).toBe(false);
  });
});
```
Run: `npx vitest run`. Expected: FAIL — cannot resolve `./socketEvents`.

- [ ] **Step 5: Write `lib/socketEvents.ts`**

```ts
import type { AssistantStatus } from '@/store/assistantStore';

export const ASSISTANT_STATUSES: readonly AssistantStatus[] = [
  'idle',
  'listening',
  'thinking',
  'responding',
  'executing_tool',
];

export interface SocketActions {
  setStatus: (status: AssistantStatus) => void;
  setTranscript: (text: string) => void;
  setActiveTool: (tool: string | null) => void;
}

export interface ServerEvent {
  type: string;
  payload: unknown;
}

export function isAssistantStatus(value: unknown): value is AssistantStatus {
  return typeof value === 'string' && (ASSISTANT_STATUSES as readonly string[]).includes(value);
}

function field(payload: unknown, key: string): unknown {
  return payload !== null && typeof payload === 'object' ? (payload as Record<string, unknown>)[key] : undefined;
}

export function applyServerEvent(event: ServerEvent, actions: SocketActions): boolean {
  const { type, payload } = event;
  switch (type) {
    case 'state_change':
      if (!isAssistantStatus(payload)) return false;
      actions.setStatus(payload);
      return true;
    case 'wake_word_detected':
      actions.setStatus('listening');
      return true;
    case 'user_transcript':
      if (typeof payload !== 'string') return false;
      actions.setTranscript(`"${payload}"`);
      return true;
    case 'ai_response':
      if (typeof payload !== 'string') return false;
      actions.setTranscript(payload);
      return true;
    case 'tool_start': {
      const name = field(payload, 'name');
      if (typeof name !== 'string') return false;
      actions.setActiveTool(name);
      return true;
    }
    case 'tool_end':
      actions.setActiveTool(null);
      return true;
    case 'error': {
      const message = field(payload, 'message');
      actions.setTranscript(`Error: ${typeof message === 'string' ? message : 'unknown error'}`);
      return true;
    }
    default:
      return false;
  }
}
```

- [ ] **Step 6: Rewrite `hooks/useSocket.ts`**

```ts
'use client';

import { useEffect, useRef } from 'react';
import { applyServerEvent } from '@/lib/socketEvents';
import { useAssistantStore } from '@/store/assistantStore';

const SOCKET_URL = process.env.NEXT_PUBLIC_JARVIS_WS_URL ?? 'ws://127.0.0.1:8000/ws';

export const useSocket = () => {
  const setStatus = useAssistantStore((state) => state.setStatus);
  const setTranscript = useAssistantStore((state) => state.setTranscript);
  const setActiveTool = useAssistantStore((state) => state.setActiveTool);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(SOCKET_URL);
    socketRef.current = ws;
    ws.onopen = () => setTranscript('Systems online.');
    ws.onclose = () => setTranscript('Connection lost.');
    ws.onmessage = (event) => {
      try {
        applyServerEvent(JSON.parse(event.data), { setStatus, setTranscript, setActiveTool });
      } catch {
        console.error('Invalid socket message', event.data);
      }
    };
    return () => ws.close();
  }, [setStatus, setTranscript, setActiveTool]);

  return socketRef;
};
```

- [ ] **Step 7: Write `scripts/ws_smoke.py`**

```python
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
```

- [ ] **Step 8: Verify everything**

```powershell
.venv/Scripts/python.exe -m pytest tests/unit -q
npx vitest run
npx tsc --noEmit
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Start -Fake -NoVoice
.venv/Scripts/python.exe scripts/ws_smoke.py "hello jarvis"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Stop
```
Expected: pytest all pass; vitest `8 passed`; tsc exit 0; smoke output is exactly five JSON lines:
`user_transcript`, `state_change thinking`, `state_change responding`, `ai_response "You said: hello jarvis"`,
`state_change idle`. Visual proof of the UI is produced in P6-T3 (no visual component changed here) — say so in the proof.

- [ ] **Step 9: Full gate, proof, commit, push (end of phase)**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add server.py electron/preload.js lib/socketEvents.ts lib/socketEvents.test.ts vitest.config.ts hooks/useSocket.ts package.json package-lock.json scripts/ws_smoke.py tests/unit/test_ws_protocol.py tests/unit/test_electron_files.py docs/proof/P1-T3.md docs/PROGRESS.md
git commit -m "feat(server): user_text over websocket with ordered state events [P1-T3]" -m "Proof: docs/proof/P1-T3.md"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1
git push origin testing
```

**Acceptance criteria**
- Event sequence test and smoke script output match exactly.
- Invalid or unknown client messages never close the socket.
- `npx vitest run`, `npx tsc --noEmit`, and the full gate exit 0.
