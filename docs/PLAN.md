# JARVIS Assistant — Master Implementation Plan

> **For the developer agent:** follow `AGENTS.md`. Execute tasks in the order listed in §7, one at a time,
> each with its own tests, proof file, and commit. Track status in `docs/PROGRESS.md`. Task details live in
> `docs/plan/phase-*.md`. This file defines the contracts every task must respect.

**Goal:** Turn the existing JARVIS project (strong 3D UI, stub backend) into a fully local, keyless, voice-driven
assistant with multi-turn conversation, model-chosen tools, persistent memory, computer actions, and MCP
integrations — every feature proven by tests.

**Architecture:** Keep the current flat layout (`assistant/` Python package + Next.js app at repo root + Electron
shell). A FastAPI server owns one `Orchestrator` (LLM agent loop over a `ToolRegistry`) and one
`VoiceController` (wake word → VAD → Whisper → Orchestrator → Kokoro with barge-in). The UI talks to the server
over a single WebSocket using the event protocol in §4.

**Tech stack:** Python 3.12, FastAPI + uvicorn, httpx, pydantic v2 + pydantic-settings, Ollama (`qwen3:8b` chat
with tools, `nomic-embed-text` embeddings), faster-whisper 1.2.x, kokoro-onnx 0.6.x, openWakeWord 0.6.x, Silero VAD,
rapidocr-onnxruntime, mss, `mcp` 2.x client, SQLite, numpy, rapidfuzz, pytest. Next.js 15, React 19, Zustand 5,
React Three Fiber, Electron 40, Playwright.

**Spec:** This file §1–§6 plus `AGENTS.md`. Background: owner's audit (findings reproduced in §1).

---

## Global Constraints

- Branch `testing` only; see `AGENTS.md` §5. Repo `https://github.com/AtharvaPatil15/Jarvis`.
- Zero API keys and zero paid/cloud services at runtime. Internet is used only for web search, weather, and model downloads.
- Python `3.12`; venv at `.venv/`; all Python commands run as `.venv/Scripts/python.exe ...`.
- Settings come only from `assistant/config.py` (`Settings`, env prefix `JARVIS_`); no literals for URLs, models, paths, location.
- Chat model default `qwen3:8b`; embedding model `nomic-embed-text`; Ollama base URL `http://127.0.0.1:11434`.
- VRAM budget 8 GB: chat model (~5.5 GB) + Whisper `small.en` on GPU; Kokoro and openWakeWord run on CPU.
- Every GPU path must fall back to CPU (`int8`) automatically and log which device was chosen.
- Audio format inside the backend: 16 kHz, mono, `int16`, frames of **1280 samples (80 ms)**.
- UI status values are exactly: `idle | listening | thinking | responding | executing_tool`.
- Do not modify `components/jarvis/layers/*`, `components/jarvis/shaders/*`, `components/jarvis/JarvisCoreEngine.tsx`.
- Voice replies: 1–2 sentences unless the user asks for detail.
- Tool loop hard cap: `max_agent_steps = 5`.
- Tests never require a physical microphone or speaker.

---

## 1. Current state (verified by reading the code, 13 Sep 2026)

| Area | State |
|---|---|
| UI | Works. R3F core, HUD, `useSocket` → `store/assistantStore.ts`; `npx tsc --noEmit` and `npm run build` pass. |
| `server.py` | Crashes after every reply: sets `voice.conv_manager.is_processing` but `VoiceController` has no `conv_manager`. Uses deprecated `@app.on_event`. Only emits `wake_word_detected` and `ai_response`; never `state_change` / `user_transcript`, so the orb never leaves `listening`. |
| `voice_main.py` | Calls `stt.listen(duration=8)`; only `listen_until_silence()` exists → crash. |
| Wake word | Porcupine keyword `"computer"`; access key hardcoded in `assistant/voice/wake_word.py` and `voice_main.py` and present in public git history. |
| STT / TTS | Google cloud STT (`recognize_google`); edge-tts writes MP3 then pygame plays it (no streaming, no barge-in). |
| LLM | `assistant/brain/llm.py` → LM Studio, single stateless prompt, no history, no tools. |
| Routing | `orchestrator.py` keyword `if` list; `Planner` never called. |
| Memory | `MemoryStore` (JSON) and `KnowledgeCache` (SQLite) never used in conversation. |
| Safety | `PermissionManager` uses `input()`; never called. |
| Tools | `smart_search` works (imports `ddgs`, but `requirements.txt` lists `duckduckgo-search`); `messaging` is a mock. |
| Config | `.env.example` lists 12 settings; no code reads any environment variable. |
| Electron | `electron/main.js` references `preload.js`, which does not exist. |
| Tests | None. |

---

## 2. Target file map

```
assistant/
  config.py                 Settings (pydantic-settings), get_settings()
  events.py                 EventType, AssistantState, Emit
  orchestrator.py           Orchestrator (async agent loop)
  runtime.py                build_llm(), build_runtime() — shared by server.py and main.py
  hub.py                    ConnectionHub (WebSocket fan-out, thread-safe emit)
  scheduler.py              ReminderScheduler
  mcp_bridge.py             MCPBridge, MCPTool
  brain/
    llm.py                  LLMClient, ChatResult, ToolCall, LLMError
    fake_llm.py             FakeLLM (deterministic, for tests and e2e)
    prompts.py              build_system_prompt()
    session.py              Session (history + trimming)
  tools/
    base.py                 BaseTool
    registry.py             ToolRegistry
    selector.py             ToolSelector (embedding relevance)
    builtin/
      __init__.py           build_default_registry()
      time_tool.py          get_time
      calculator.py         calculate
      web_search.py         web_search, fetch_page
      weather.py            get_weather
      memory_tools.py       remember, recall, forget
      system.py             open_app, open_url, media_control
      files.py              search_files, read_file
      screen.py             read_screen
      reminders.py          set_reminder, list_reminders
  safety/
    permissions.py          PermissionGate, AllowAllGate, DenyAllGate, WebSocketPermissionGate
  memory/
    db.py                   MemoryDB (SQLite)
    manager.py              MemoryManager, Fact
    redact.py               redact()
  voice/
    audio_io.py             AudioSource, MicSource, WavSource, AudioSink, SpeakerSink, NullSink, resample
    wake.py                 WakeWordDetector
    vad.py                  SpeechSegmenter
    stt.py                  Transcriber
    tts.py                  Synthesizer, split_sentences, SentenceBuffer
    echo.py                 EchoGuard
    controller.py           VoiceController
server.py                   create_app() (uvicorn factory)
main.py                     text CLI
start_backend.py            runs uvicorn factory
scripts/
  verify_all.ps1            quality gate
  backend.ps1               start/stop the backend in the background for proofs
  ensure_ollama.py          start Ollama and pull models
  ws_smoke.py               send one text command over the WebSocket and print events
  conversation_smoke.py     multi-turn live conversation over the WebSocket
  probe_llm.py              Ollama capability probe
  download_models.py        fetch Whisper/Kokoro/openWakeWord assets into models/
  run_evals.py              spoken-command eval runner
  start_jarvis.ps1          one-command launcher
evals/commands.yaml
tests/unit/ tests/live/ tests/models/ tests/e2e/ tests/conftest.py tests/fixtures/
lib/jarvisSocket.ts         WebSocket client with reconnect
components/overlay/CommandInput.tsx, PermissionPrompt.tsx
electron/preload.js
mcp_servers.json
docs/PLAN.md docs/plan/phase-*.md docs/PROGRESS.md docs/DECISIONS.md docs/proof/
```

Deleted by the end: `assistant/brain/planner.py`, `assistant/tools/messaging.py`, `assistant/tools/search.py`,
`assistant/tools/smart_search.py` (replaced), `assistant/memory/store.py`, `assistant/memory/cache.py`,
`assistant/memory/contacts.py`, `assistant/memory/user_profile.py`, `assistant/voice/conversation_manager.py`,
`assistant/voice/voice_controller.py`, `assistant/voice/wake_word.py`, `assistant/safety/` old `PermissionManager`,
`assistant/ui/overlay.py`, `assistant/ui/hud.html`, `assistant/ui/libs/`, `voice_main.py`, `install_ui_deps.py`,
`components/ai-core/*`, `response_*.mp3`. Each deletion happens in the task named in its phase file, after `grep`
proves nothing imports it.

---

## 3. Interfaces (contracts — names and signatures are binding)

### 3.1 `assistant/config.py`
```python
class Settings(BaseSettings):  # env_prefix="JARVIS_", env_file=".env", extra="ignore"
    ollama_url: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen3:8b"
    embed_model: str = "nomic-embed-text"
    llm_backend: Literal["ollama", "fake"] = "ollama"
    llm_timeout_s: float = 120.0
    llm_disable_thinking: bool = True
    user_description: str = "Final-year engineering student"
    location_name: str = "Pimpri-Chinchwad, Maharashtra, India"
    latitude: float = 18.6298
    longitude: float = 73.7997
    timezone: str = "Asia/Kolkata"
    data_dir: Path = Path("data")
    models_dir: Path = Path("models")
    whisper_model: str = "small.en"
    whisper_device: Literal["auto", "cuda", "cpu"] = "auto"
    tts_voice: str = "bm_george"
    tts_speed: float = 1.1
    wake_model: str = "hey_jarvis"
    wake_threshold: float = 0.5
    vad_silence_ms: int = 600
    voice_enabled: bool = True
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    max_agent_steps: int = 5
    history_max_chars: int = 12000
    permission_timeout_s: float = 30.0
    file_roots: list[Path] = [Path.home() / "Documents", Path.home() / "Desktop", Path.home() / "Downloads"]
    mcp_config_path: Path = Path("mcp_servers.json")
    porcupine_access_key: str = ""   # legacy wake word only; removed in P3-T6
def get_settings() -> Settings: ...   # functools.lru_cache
```

### 3.2 `assistant/events.py`
```python
class EventType(StrEnum):
    STATE_CHANGE = "state_change"; WAKE_WORD_DETECTED = "wake_word_detected"
    USER_TRANSCRIPT = "user_transcript"; AI_RESPONSE_DELTA = "ai_response_delta"; AI_RESPONSE = "ai_response"
    TOOL_START = "tool_start"; TOOL_END = "tool_end"; PERMISSION_REQUEST = "permission_request"
    REMINDER = "reminder"; ERROR = "error"
class AssistantState(StrEnum):
    IDLE = "idle"; LISTENING = "listening"; THINKING = "thinking"
    RESPONDING = "responding"; EXECUTING_TOOL = "executing_tool"
Emit = Callable[[str, Any], None]
```

### 3.3 `assistant/brain/llm.py`
```python
@dataclass(frozen=True)
class ToolCall: id: str; name: str; arguments: dict[str, Any]
@dataclass(frozen=True)
class ChatResult: content: str; tool_calls: list[ToolCall]
class LLMError(RuntimeError): ...
class LLMClient:
    def __init__(self, base_url: str, model: str, embed_model: str, timeout_s: float = 120.0,
                 disable_thinking: bool = True, transport: httpx.BaseTransport | None = None) -> None
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
             temperature: float = 0.4, max_tokens: int = 512,
             on_delta: Callable[[str], None] | None = None) -> ChatResult
    def embed(self, texts: list[str]) -> list[list[float]]
    def health(self) -> bool
```
Uses Ollama native API: `POST /api/chat` (`stream` true iff `on_delta` given; `think: false` when
`disable_thinking`; `options.temperature`, `options.num_predict`), `POST /api/embed`, `GET /api/tags`.
Strips any `<think>…</think>` from content. `FakeLLM` in `brain/fake_llm.py` has the same `chat`/`embed`/`health`
signatures.

### 3.4 `assistant/brain/session.py` and `prompts.py`
```python
class Session:
    def __init__(self, system_prompt: Callable[[], str], max_chars: int = 12000) -> None
    def add_user(self, text: str) -> None
    def add_assistant(self, content: str, tool_calls: list[ToolCall] | None = None) -> None
    def add_tool_result(self, call: ToolCall, content: str) -> None
    def messages(self) -> list[dict[str, Any]]   # system first; oldest turns dropped to fit max_chars;
                                                  # never separates an assistant tool_calls message from its tool results
    def clear(self) -> None
def build_system_prompt(settings: Settings, now: datetime, memories: Sequence[str] = ()) -> str
```
Message shapes (Ollama native): `{"role":"assistant","content":"","tool_calls":[{"function":{"name":str,"arguments":dict}}]}`
and `{"role":"tool","tool_name":str,"content":str}`.

### 3.5 Tools
```python
class BaseTool(ABC):
    name: ClassVar[str]; description: ClassVar[str]; Args: ClassVar[type[BaseModel]]
    requires_permission: ClassVar[bool] = False
    def parameters(self) -> dict[str, Any]             # default: self.Args.model_json_schema()
    def parse_args(self, raw: dict[str, Any]) -> BaseModel   # default: self.Args.model_validate(raw)
    def schema(self) -> dict[str, Any]                 # {"type":"function","function":{"name","description","parameters"}}
    def permission_summary(self, args: BaseModel) -> str
    @abstractmethod
    def run(self, args: BaseModel) -> str
class ToolRegistry:
    def register(self, tool: BaseTool) -> None          # ValueError on duplicate name
    def get(self, name: str) -> BaseTool | None
    def names(self) -> list[str]
    def all(self) -> list[BaseTool]
    def schemas(self, names: Iterable[str] | None = None) -> list[dict[str, Any]]
class ToolSelector:
    def __init__(self, llm: LLMClient, always_include: Sequence[str] = ("get_time", "recall")) -> None
    def select(self, query: str, registry: ToolRegistry, k: int = 12) -> list[str]
def build_default_registry(settings: Settings, memory: MemoryManager | None = None,
                           scheduler: ReminderScheduler | None = None) -> ToolRegistry
```
Tool errors are returned as strings starting with `ERROR:` — tools never raise into the agent loop.

### 3.6 `assistant/safety/permissions.py`
```python
class PermissionGate(Protocol):
    async def request(self, tool_name: str, summary: str) -> bool
class AllowAllGate: ...   class DenyAllGate: ...
class WebSocketPermissionGate:
    def __init__(self, emit: Emit, timeout_s: float = 30.0) -> None
    async def request(self, tool_name: str, summary: str) -> bool   # emits PERMISSION_REQUEST {id, tool, summary}; timeout → False
    def resolve(self, request_id: str, allowed: bool) -> None
```

### 3.7 `assistant/orchestrator.py`
```python
class Orchestrator:
    def __init__(self, llm: LLMClient, registry: ToolRegistry, session: Session, gate: PermissionGate,
                 emit: Emit, memory: MemoryManager | None = None, selector: ToolSelector | None = None,
                 max_steps: int = 5) -> None
    async def handle(self, text: str, on_delta: Callable[[str], None] | None = None) -> str
```
Emits, in order: `state_change thinking` → for each tool call `state_change executing_tool`, `tool_start {id,name,arguments}`,
`tool_end {id,name,ok,summary}`, then `state_change thinking` again → `state_change responding` (at the first streamed
chunk of the final answer) → `ai_response_delta` chunks → `ai_response <final text>`. **The caller** (server text path or
voice controller) emits `user_transcript` before calling and `state_change idle` after it has finished (after speech).
Blocking LLM/tool calls run in `asyncio.to_thread`; `on_delta` is invoked from that worker thread. On `LLMError`: emit
`error {message}` and return a short spoken apology (still emitted as `responding` + `ai_response`). Blank input returns
`""` and emits nothing.

### 3.8 Memory
```python
@dataclass(frozen=True)
class Fact: id: int; text: str; score: float
class MemoryDB:
    def __init__(self, path: Path) -> None
    def add_message(self, session_id: str, role: str, content: str) -> int
    def recent_messages(self, session_id: str, limit: int) -> list[tuple[str, str]]
    def add_fact(self, text: str, embedding: list[float]) -> int
    def all_facts(self) -> list[tuple[int, str, np.ndarray]]
    def delete_fact(self, fact_id: int) -> bool
    def add_reminder(self, text: str, due_at: datetime) -> int
    def due_reminders(self, now: datetime) -> list[tuple[int, str, datetime]]
    def pending_reminders(self) -> list[tuple[int, str, datetime]]
    def mark_reminder_done(self, reminder_id: int) -> None
class MemoryManager:
    def __init__(self, db: MemoryDB, llm: LLMClient, dedupe_threshold: float = 0.9) -> None
    def log_turn(self, session_id: str, role: str, content: str) -> None     # redacts before storing
    def remember(self, text: str) -> int | None                               # None when a near-duplicate exists
    def search(self, query: str, k: int = 5, min_score: float = 0.35) -> list[Fact]
    def forget(self, fact_id: int) -> bool
    def extract_facts(self, user_text: str, assistant_text: str) -> list[str]
    def process_exchange(self, user_text: str, assistant_text: str) -> list[int]
def redact(text: str) -> str
```

### 3.9 Voice
```python
SAMPLE_RATE = 16000; FRAME_SAMPLES = 1280
class AudioSource(Protocol):
    def frames(self) -> Iterator[np.ndarray]          # int16 mono, FRAME_SAMPLES each
class MicSource: def __init__(self, device: int | None = None) -> None
class WavSource: def __init__(self, audio: Path | np.ndarray, realtime: bool = False, tail_silence_s: float = 1.0) -> None
class AudioSink(Protocol):
    def play(self, samples: np.ndarray, sample_rate: int) -> None   # non-blocking, queues
    def stop(self) -> None
    @property
    def is_playing(self) -> bool
    def wait(self) -> None
class SpeakerSink: ...  class NullSink: played: list[np.ndarray]
def resample(samples: np.ndarray, src_rate: int, dst_rate: int = SAMPLE_RATE) -> np.ndarray
class WakeWordDetector:
    def __init__(self, model_name: str = "hey_jarvis", threshold: float = 0.5) -> None
    def score(self, frame: np.ndarray) -> float
    def detected(self, frame: np.ndarray) -> bool
    def reset(self) -> None
class SpeechSegmenter:
    def __init__(self, silence_ms: int = 600, min_speech_ms: int = 250, max_utterance_s: float = 15.0) -> None
    def is_speech(self, frame: np.ndarray) -> bool
    def feed(self, frame: np.ndarray) -> np.ndarray | None   # completed utterance (int16) or None
    @property
    def speech_active(self) -> bool
    def reset(self) -> None
class Transcriber:
    def __init__(self, model_size: str = "small.en", device: str = "auto", download_root: Path | None = None) -> None
    device: str; compute_type: str
    def transcribe(self, audio: np.ndarray) -> str
def split_sentences(text: str) -> list[str]
class SentenceBuffer:
    def push(self, delta: str) -> list[str]
    def flush(self) -> list[str]
class Synthesizer:
    def __init__(self, model_dir: Path, voice: str = "bm_george", speed: float = 1.1) -> None
    def voices(self) -> list[str]
    def synthesize(self, text: str) -> tuple[np.ndarray, int]   # float32 samples, sample rate
class EchoGuard:
    def __init__(self, threshold: int = 80, window_s: float = 8.0) -> None
    def note_spoken(self, text: str) -> None
    def is_echo(self, transcript: str) -> bool
Handler = Callable[[str, Callable[[str], None]], Awaitable[str]]   # (text, on_delta) -> final text
class VoiceController:
    def __init__(self, source: AudioSource, sink: AudioSink, wake: WakeWordDetector, segmenter: SpeechSegmenter,
                 stt: Transcriber, tts: Synthesizer, handler: Handler, emit: Emit,
                 follow_up_s: float = 6.0, barge_in_ms: int = 300) -> None
    async def run(self, stop: asyncio.Event) -> None
```

### 3.9a Voice interface additions (binding; they extend §3.9)
```python
# audio_io.py
FRAME_SECONDS = FRAME_SAMPLES / SAMPLE_RATE              # 0.08
def to_int16(samples: np.ndarray) -> np.ndarray
def to_float32(samples: np.ndarray) -> np.ndarray
def chunk_frames(samples: np.ndarray, frame_samples: int = FRAME_SAMPLES) -> list[np.ndarray]   # zero-pads the last frame
def silence(seconds: float) -> np.ndarray                 # int16 zeros at SAMPLE_RATE
class WavSource: def __init__(self, audio: Path | np.ndarray, realtime: bool = False,
                              lead_silence_s: float = 0.0, tail_silence_s: float = 1.0) -> None
class NullSink: def __init__(self, simulate_playback: bool = False) -> None   # played: list[np.ndarray]; stopped: int
# tts.py
class Synthesizer: def synthesize(self, text: str, voice: str | None = None) -> tuple[np.ndarray, int]
# vad.py
class SileroFrameVAD: def __call__(self, frame: np.ndarray) -> float; def reset(self) -> None
class SpeechSegmenter: def __init__(self, silence_ms: int = 600, min_speech_ms: int = 250, max_utterance_s: float = 15.0,
                                    threshold: float = 0.5, vad: Callable[[np.ndarray], float] | None = None,
                                    pre_roll_ms: int = 240) -> None
# stt.py
class Transcriber: def __init__(self, model_size: str = "small.en", device: str = "auto",
                                download_root: Path | None = None, model_factory: Callable[..., Any] | None = None) -> None
# wake.py
class WakeWordDetector: def __init__(self, model_name: str = "hey_jarvis", threshold: float = 0.5, model: Any | None = None) -> None
# controller.py
class VoiceController: async def speak(self, text: str) -> None          # synthesize + play + wait (used for typed commands)
```
Legacy modules are renamed in P3-T1 (`assistant/voice/stt.py` → `legacy_stt.py`, `tts.py` → `legacy_tts.py`) so the new
`stt.py` / `tts.py` can take their names; all legacy voice code is deleted in P3-T6.

### 3.10 Server, scheduler, MCP
```python
def create_app(settings: Settings | None = None, *, llm: LLMClient | None = None,
               enable_voice: bool | None = None) -> FastAPI      # uvicorn "server:create_app" --factory
class ConnectionHub:                                                # all sends go through one FIFO queue (ordered)
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None    # call inside lifespan; starts the sender task
    async def close(self) -> None
    @property
    def client_count(self) -> int
    async def connect(self, ws: WebSocket) -> None
    def disconnect(self, ws: WebSocket) -> None
    async def broadcast(self, type_: str, payload: Any) -> None
    async def drain(self) -> None                                    # wait until queued messages are sent
    @property
    def loop(self) -> asyncio.AbstractEventLoop
    def emit(self, type_: str, payload: Any) -> None                 # thread-safe; usable as Emit
class ReminderScheduler:
    def __init__(self, db: MemoryDB, on_due: Callable[[int, str], None], poll_s: float = 5.0) -> None
    def start(self) -> None; def stop(self) -> None
    def schedule(self, text: str, due_at: datetime) -> int
class MCPBridge:
    def __init__(self, config_path: Path) -> None
    def start(self) -> list[BaseTool]      # runs its own event-loop thread; tool names "mcp__<server>__<tool>"
    def stop(self) -> None
```
HTTP: `GET /health` → `{"status":"ok","llm":bool,"voice":bool}`.

---

## 4. WebSocket protocol (`ws://127.0.0.1:8000/ws`)

Every message is JSON `{"type": string, "payload": any}`.

| Direction | type | payload |
|---|---|---|
| server→client | `state_change` | `"idle" \| "listening" \| "thinking" \| "responding" \| "executing_tool"` |
| server→client | `wake_word_detected` | `null` |
| server→client | `user_transcript` | `string` |
| server→client | `ai_response_delta` | `string` (chunk) |
| server→client | `ai_response` | `string` (final full text) |
| server→client | `tool_start` | `{"id": string, "name": string, "arguments": object}` |
| server→client | `tool_end` | `{"id": string, "name": string, "ok": boolean, "summary": string}` |
| server→client | `permission_request` | `{"id": string, "tool": string, "summary": string}` |
| server→client | `reminder` | `{"id": number, "text": string}` |
| server→client | `error` | `{"message": string}` |
| client→server | `user_text` | `string` |
| client→server | `permission_response` | `{"id": string, "allowed": boolean}` |

---

## 5. Testing layout

```
tests/conftest.py        shared fixtures: settings (tmp data_dir), fake_llm, registry, emitted-events recorder
tests/unit/              no marker — offline, < 30 s total
tests/live/              @pytest.mark.live   — real Ollama
tests/models/            @pytest.mark.models — real Whisper/Kokoro/openWakeWord files, no mic/speaker
tests/e2e/               @pytest.mark.e2e    — real servers; Playwright specs live in e2e/
tests/fixtures/          small text fixtures only (audio is generated at test time into tmp_path)
```
Commands:
- Quick: `.venv/Scripts/python.exe -m pytest -m "not live and not models and not e2e" -q`
- Live: `.venv/Scripts/python.exe -m pytest -m live -q`
- Models: `.venv/Scripts/python.exe -m pytest -m models -q`
- Frontend: `npx tsc --noEmit` and `npm run build`
- Browser e2e: `npx playwright test`

---

## 6. Final definition of done (checked in P6-T6)

1. `scripts/verify_all.ps1` exits 0 (all markers, tsc, build, Playwright, secret scan).
2. `scripts/run_evals.py` ≥ 85 % pass on `evals/commands.yaml` with the live model.
3. Voice round-trip test (Kokoro → Whisper) word error rate ≤ 0.15.
4. Memory persists across a backend restart (live test).
5. `git grep` finds no Porcupine key, no `recognize_google`, no `edge_tts`, no `pvporcupine`.
6. `scripts/start_jarvis.ps1` brings up Ollama + backend + UI + Electron and `/health` returns ok.
7. All work is on `origin/testing`; `main` and `Test` untouched.

---

## 7. Task index

| ID | Task | Depends on | File |
|---|---|---|---|
| P0-T1 | Git baseline on branch `testing` | — | `docs/plan/phase-0-bootstrap.md` |
| P0-T2 | Python venv, test harness, `verify_all.ps1` | P0-T1 | phase-0 |
| P0-T3 | Ollama models + capability probe | P0-T2 | phase-0 |
| P0-T4 | `Settings` + `events.py` | P0-T2 | phase-0 |
| P1-T1 | Server app factory, lifespan, crash fix, `FakeLLM` | P0-T4 | `docs/plan/phase-1-fixes.md` |
| P1-T2 | `voice_main.py` fix, `ddgs` dependency, key out of source | P1-T1 | phase-1 |
| P1-T3 | `user_text` over WS + state events + UI wiring + Electron preload | P1-T1 | phase-1 |
| P2-T1 | `LLMClient` (Ollama native, streaming, embeddings) | P0-T3, P0-T4 | `docs/plan/phase-2-brain.md` |
| P2-T2 | `BaseTool`, `ToolRegistry`, `get_time`, `calculate` | P0-T4 | phase-2-brain |
| P2-T3 | `Session` + `build_system_prompt` | P2-T1 | phase-2-brain |
| P2-T4 | Permission gates + `Orchestrator` agent loop | P2-T2, P2-T3 | `docs/plan/phase-2-agent.md` |
| P2-T5 | `web_search`, `fetch_page`, `get_weather` | P2-T2 | phase-2-agent |
| P2-T6 | Wire orchestrator into server + live conversation proof | P2-T4, P2-T5, P1-T3 | phase-2-agent |
| P3-T1 | Model downloader + `Synthesizer` + sentence splitting | P0-T2 | `docs/plan/phase-3-voice.md` |
| P3-T2 | `Transcriber` + TTS→STT round-trip test | P3-T1 | phase-3-voice |
| P3-T3 | `SpeechSegmenter` (Silero VAD) | P3-T1 | phase-3-voice |
| P3-T4 | `WakeWordDetector` (openWakeWord) | P3-T1 | phase-3-voice |
| P3-T5 | Audio IO, `EchoGuard`, `VoiceController` with barge-in | P3-T2, P3-T3, P3-T4 | `docs/plan/phase-3-controller.md` |
| P3-T6 | Voice into server, remove old voice stack, latency proof | P3-T5, P2-T6 | phase-3-controller |
| P4-T1 | `MemoryDB` + `redact` + turn logging | P2-T6 | `docs/plan/phase-4-memory.md` |
| P4-T2 | `MemoryManager.remember/search/forget` + prompt injection | P4-T1 | phase-4 |
| P4-T3 | Fact extraction + memory tools | P4-T2 | phase-4 |
| P4-T4 | Restart-persistence live proof | P4-T3 | phase-4 |
| P5-T1 | `open_app`, `open_url`, `media_control` | P2-T6 | `docs/plan/phase-5-actions.md` |
| P5-T2 | `search_files`, `read_file` | P2-T6 | phase-5 |
| P5-T3 | `read_screen` (OCR) | P2-T6 | phase-5 |
| P5-T4 | Reminders + scheduler | P4-T1 | phase-5 |
| P5-T5 | `MCPBridge` (filesystem server proof) | P2-T6 | phase-5 |
| P5-T6 | `ToolSelector` + dead-code removal | P5-T5 | phase-5 |
| P6-T1 | `lib/jarvisSocket.ts` + store + streaming UI | P2-T6 | `docs/plan/phase-6-product.md` |
| P6-T2 | `CommandInput` + `PermissionPrompt` components | P6-T1 | phase-6 |
| P6-T3 | Playwright end-to-end with screenshots | P6-T2 | phase-6 |
| P6-T4 | `start_jarvis.ps1` launcher | P3-T6, P6-T1 | phase-6 |
| P6-T5 | Eval suite ≥ 85 % | P5-T6, P4-T4 | phase-6 |
| P6-T6 | Cleanup, README, final full verification, push | all | phase-6 |
