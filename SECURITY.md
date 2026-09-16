# Security Policy

## Local-only Design

JARVIS Assistant is designed to run **fully locally** with zero cloud dependencies at runtime:

- **Chat & embeddings**: Ollama (`qwen3:8b`, `nomic-embed-text`) on `http://127.0.0.1:11434`
- **Speech-to-text**: faster-whisper (`small.en`) on GPU/CPU
- **Text-to-speech**: Kokoro ONNX (`bm_george`) on CPU
- **Wake word**: openWakeWord (`hey_jarvis`) on CPU
- **VAD**: Silero VAD on CPU
- **OCR**: RapidOCR ONNX on CPU
- **Web search**: DuckDuckGo through the `ddgs` package; `fetch_page` downloads a page the model chose (public
  addresses only)
- **Weather**: Open-Meteo geocoding and forecast APIs
- **Model downloads**: Ollama, Hugging Face (Whisper, Kokoro), openWakeWord — only during setup

No API keys, accounts, logins, sign-ups, or paid services are required or used.

## Permission Model

Tools marked `requires_permission` are only run after the user answers an Allow/Deny prompt sent over the WebSocket
(`permission_request` / `permission_response`). A prompt that is not answered within `JARVIS_PERMISSION_TIMEOUT_S`
(default 30 s) counts as **deny**.

| Tool | Asks first |
|------|------------|
| `read_file` | Yes |
| `read_screen` | Yes |
| `forget` | Yes |
| MCP tools | Yes, unless the server entry in `mcp_servers.json` sets `"requires_permission": false` |
| `get_time`, `calculate`, `get_weather`, `web_search`, `fetch_page`, `search_files`, `open_app`, `open_url`, `media_control`, `set_reminder`, `list_reminders`, `remember`, `recall` | No |

`open_url` only accepts `http`/`https` URLs, and `read_file` / `search_files` are limited to `JARVIS_FILE_ROOTS`
(Documents, Desktop and Downloads by default) with path traversal refused. File and screen text is given to the model
under an "untrusted content" header so that instructions inside it are treated as data.

## Secret Redaction

Before any text is written to the SQLite database, `assistant.memory.redact.redact()` replaces:
- API-key-like tokens (`sk-…`, `ghp_…` and other GitHub token prefixes, `AIza…`)
- Email addresses
- Card-like numbers (13–19 digits)
- 12-digit ID numbers
- Phone numbers
- The value after `password`, `passcode`, `pin` or `otp`

## Data Storage

All persistent data lives under `data/` (git-ignored):
- `jarvis.db` — SQLite: messages, facts (with embeddings), reminders
- `launcher/` — PID files and logs for the one-command launcher
- No audio files are stored by default.

## Historical Note

An old Porcupine access key is present in the early git history of `main` (hardcoded in `assistant/voice/wake_word.py`
and `voice_main.py`). Task P0-T1 removed it from the source before `testing` was created, and the project now uses the
keyless openWakeWord model (P3-T4), so the key is no longer used. The owner should revoke that key in the Picovoice
Console.

## Reporting a Vulnerability

If you discover a security vulnerability, email the repository maintainer (DO NOT open a public issue). Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Supported Versions

| Branch | Status |
|--------|--------|
| `testing` | Active development |

## Known Considerations

1. **Local execution** — Tools execute code locally based on model-chosen actions. Review tool implementations in `assistant/tools/builtin/`.
2. **Network requests** — Only web search, page fetching, weather and setup-time model downloads leave the machine.
3. **Wake word** — openWakeWord runs continuously when voice is enabled; it processes audio locally.
4. **Barge-in** — User speech during TTS playback interrupts synthesis; the interrupted audio is discarded.
5. **Microphone access** — Required for voice mode; see `scripts/voice_hardware_check.py`.