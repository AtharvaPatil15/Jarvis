# Jarvis Assistant

Jarvis Assistant is an archived personal experiment built as a small monorepo with three app surfaces:

- `apps/web` for the holographic Next.js UI
- `apps/desktop` for the Electron shell
- `apps/backend` for the Python voice assistant and FastAPI server

The repository is kept as a reference codebase, not as an actively maintained production system.

## Monorepo Layout

```text
jarvis-assistant/
|-- apps/
|   |-- backend/
|   |   |-- run_cli.py
|   |   |-- run_server.py
|   |   |-- run_voice.py
|   |   |-- requirements.txt
|   |   `-- src/jarvis_backend/
|   |-- desktop/
|   |   |-- main.js
|   |   `-- preload.js
|   `-- web/
|       |-- next.config.js
|       |-- postcss.config.js
|       |-- tailwind.config.ts
|       |-- tsconfig.json
|       `-- src/
|-- config/
|   `-- local/
|-- data/
|   |-- runtime/
|   `-- state/
|-- docs/
|-- scripts/
|-- package.json
|-- package-lock.json
|-- pyrightconfig.json
`-- .env.example
```

## Apps

### Web

- Path: `apps/web`
- Stack: Next.js, React, TypeScript, Three.js, Zustand
- Purpose: holographic JARVIS-style visualization and overlay UI

### Desktop

- Path: `apps/desktop`
- Stack: Electron
- Purpose: transparent desktop shell that loads the web app

### Backend

- Path: `apps/backend`
- Stack: Python, FastAPI, SpeechRecognition, Edge TTS, Porcupine
- Purpose: orchestration, wake word, STT/TTS, and WebSocket server

## Runtime Data

Runtime and local-only artifacts are separated from source code:

- `data/state/` for local memory and assistant context
- `data/runtime/audio/` for generated or captured audio artifacts
- `config/local/` for machine-local secrets such as `key.txt`

## Getting Started

### Web dependencies

```bash
npm install
```

### Backend dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r apps/backend/requirements.txt
```

## Development Commands

### Start web app

```bash
npm run dev:web
```

### Start backend

```bash
python apps/backend/run_server.py
```

### Start Electron shell

```bash
npm run desktop
```

### Windows helper

```bat
scripts\windows\start_jarvis.bat
```

## Notes

- The backend source package is `jarvis_backend` under `apps/backend/src/`.
- The frontend source lives in `apps/web/src/`.
- The repository is cleaner and more modular now, but the application logic itself is still an old prototype.
- Some behavioral inconsistencies from the original project still remain and would need a dedicated modernization pass.

## License

See [LICENSE](LICENSE).
