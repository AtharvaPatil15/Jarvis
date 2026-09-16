# JARVIS Assistant

A fully local, keyless, voice-driven AI assistant with a holographic 3D UI, multi-turn conversation, model-chosen tools, persistent memory, computer actions, and MCP integrations. Runs entirely offline except for web search, weather, and model downloads.

## ✨ Features

- **"Hey Jarvis" wake word** — openWakeWord, no access key required
- **Local speech I/O** — faster-whisper STT, Kokoro TTS with sentence streaming and barge-in
- **Typed commands** — WebSocket-connected input box, works without a microphone
- **Tools** — time, calculator, weather, web search & page fetch, open apps/URLs, media keys, file search/read, create folders, screen OCR, reminders
- **Long-term memory** — semantic fact store with SQLite + embeddings, auto-extraction from conversation
- **MCP servers** — filesystem server included; add more via `mcp_servers.json`
- **Permission prompts** — reading a file, creating a folder, reading the screen, forgetting a memory and MCP tools ask before acting
- **3D holographic UI** — React Three Fiber orb with state-responsive visuals
- **Desktop window** — Electron shell, one-command launch/stop

## Requirements

- Windows 11
- Python 3.12
- Node 22, npm 11
- Ollama 0.34+ (models are pulled by `scripts/ensure_ollama.py`)
- ~10 GB disk for models (qwen3:8b, nomic-embed-text, Whisper, Kokoro, openWakeWord)
- NVIDIA GPU optional (Whisper uses CUDA when available, otherwise the CPU)

## Setup

```powershell
# 1. Python environment
py -3.12 -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt

# 2. Node dependencies
npm install

# 3. Pull Ollama models
.venv/Scripts/python.exe scripts/ensure_ollama.py

# 4. Download voice models (Whisper, Kokoro, openWakeWord)
.venv/Scripts/python.exe scripts/download_models.py
```

## Running

### Desktop (recommended)
Double-click `start_jarvis.bat` or run:
```powershell
scripts/start_jarvis.ps1
```
This starts Ollama (if needed), the FastAPI backend on `:8000`, the Next.js production UI on `:3000`, and an Electron window. Close the window to stop everything, or run `scripts/start_jarvis.ps1 -Stop`.

Options:
- `-NoElectron` — run headless (backend + UI only)
- `-Fake` — use `FakeLLM` (no Ollama), voice disabled
- `-Rebuild` — force `npm run build` before starting
- `-TimeoutSec N` — HTTP wait timeout (default 300)

### Text-only CLI
```powershell
.venv/Scripts/python.exe main.py
```

### Microphone check
```powershell
.venv/Scripts/python.exe scripts/voice_hardware_check.py
```

## Configuration

Every setting is a `JARVIS_*` environment variable or `.env` entry. Defaults live in `assistant/config.py`.

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API base |
| `CHAT_MODEL` | `qwen3:8b` | Chat model name |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `LLM_BACKEND` | `ollama` | `ollama` or `fake` |
| `LLM_TIMEOUT_S` | `120.0` | LLM request timeout |
| `LLM_DISABLE_THINKING` | `true` | Ask qwen3 to answer without a thinking phase (`think: false`) |
| `USER_DESCRIPTION` | `Final-year engineering student` | Injected into system prompt |
| `LOCATION_NAME` | `Pimpri-Chinchwad, Maharashtra, India` | Weather location label |
| `LATITUDE` | `18.6298` | Weather latitude |
| `LONGITUDE` | `73.7997` | Weather longitude |
| `TIMEZONE` | `Asia/Kolkata` | IANA timezone |
| `DATA_DIR` | `data` | SQLite, logs, etc. |
| `MODELS_DIR` | `models` | Whisper/Kokoro/wake models |
| `WHISPER_MODEL` | `small.en` | faster-whisper model |
| `WHISPER_DEVICE` | `auto` | `auto`, `cuda`, `cpu` |
| `TTS_VOICE` | `bm_george` | Kokoro voice |
| `TTS_SPEED` | `1.1` | Speech speed multiplier |
| `WAKE_MODEL` | `hey_jarvis` | openWakeWord model |
| `WAKE_THRESHOLD` | `0.5` | Wake detection threshold |
| `VAD_SILENCE_MS` | `600` | Silero silence cutoff |
| `VOICE_ENABLED` | `true` | Enable voice pipeline |
| `SERVER_HOST` | `127.0.0.1` | FastAPI bind address |
| `SERVER_PORT` | `8000` | FastAPI port |
| `MAX_AGENT_STEPS` | `5` | Tool loop hard cap |
| `HISTORY_MAX_CHARS` | `12000` | Conversation truncation |
| `PERMISSION_TIMEOUT_S` | `30.0` | Prompt timeout |
| `FILE_ROOTS` | `["~/Documents","~/Desktop","~/Downloads"]` | File tool search roots |
| `MCP_CONFIG_PATH` | `mcp_servers.json` | MCP server definitions |

## Privacy & Permissions

- **Fully local processing** — no cloud APIs for chat, STT, TTS, wake word, OCR, or embeddings. The only network calls are web search (DuckDuckGo via `ddgs`), page fetching (`fetch_page`, public addresses only), weather (Open-Meteo) and model downloads.
- **Permission model** — `read_file`, `create_folder`, `read_screen`, `forget` and every MCP tool (unless its entry in `mcp_servers.json` sets `"requires_permission": false`) emit a `permission_request` over the WebSocket; the UI shows an Allow/Deny prompt, and an unanswered prompt is denied after `PERMISSION_TIMEOUT_S` (30 s). Opening apps and URLs, media keys, reminders, memory saving and searching file names run without asking.
- **Untrusted content** — file text and screen text are passed to the model labelled as untrusted data, never as instructions.
- **Redaction** — before anything is written to the database, API-key-like tokens, email addresses, card numbers, 12-digit ID numbers, phone numbers and the value after "password / passcode / pin / otp" are replaced with placeholders.
- **Data location** — all persistent data lives under `data/` (ignored by git): `jarvis.db` (messages, facts, reminders), logs, launcher state.

## Development

### Architecture (text diagram)
```
UI (Next.js + R3F) ──WS──▶ FastAPI (:8000)
    │                         │
    │                    ┌────┴────┐
    │                    ▼         ▼
    │              Orchestrator  VoiceController
    │                    │         │
    │              ┌─────┴─────┐   │
    │              ▼           ▼   │
    │         ToolRegistry   STT/TTS
    │              │           │
    │         ┌────┴────┐  Wake/VAD
    │         ▼         ▼
    │      Builtin    MCP
    │      Tools     Bridge
    │
    └── Electron (optional)
```

### Commands
```powershell
# Quick gate (unit tests, tsc, vitest, secret scan)
scripts/verify_all.ps1 -Quick

# Full gate (adds live, models, e2e, Playwright)
scripts/verify_all.ps1

# Python unit tests only
.venv/Scripts/python.exe -m pytest -m "not live and not models and not e2e" -q

# Live tests (needs Ollama)
.venv/Scripts/python.exe -m pytest -m live -q

# Model tests (needs downloaded model files)
.venv/Scripts/python.exe -m pytest -m models -q

# Browser e2e (starts real servers)
npm run e2e

# Spoken-command evals
.venv/Scripts/python.exe scripts/run_evals.py
```

### Test markers (pytest.ini)
- (none) — pure unit, fast, offline
- `live` — real Ollama server
- `models` — real Whisper/Kokoro/openWakeWord files, no network after download
- `e2e` — real servers + Playwright/Edge

## License

MIT