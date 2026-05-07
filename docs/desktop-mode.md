# Desktop Mode

Desktop mode runs three separate app surfaces from the monorepo:

1. `apps/backend` for the FastAPI and voice runtime
2. `apps/web` for the holographic UI
3. `apps/desktop` for the Electron shell

## Quick Start

### Windows helper

```bat
scripts\windows\start_jarvis.bat
```

### Manual startup

```bash
python apps/backend/run_server.py
npm run dev:web
npm run desktop
```

## Architecture

### Backend

- Entry point: `apps/backend/run_server.py`
- App module: `apps/backend/src/jarvis_backend/server.py`
- WebSocket endpoint: `ws://localhost:8000/ws`

### Web

- App path: `apps/web`
- Source path: `apps/web/src`

### Desktop

- Electron entry point: `apps/desktop/main.js`
- Preload script: `apps/desktop/preload.js`

## Notes

- This remains an archived prototype, not a polished desktop product.
- Voice and audio behavior still depend on local hardware and third-party services.
