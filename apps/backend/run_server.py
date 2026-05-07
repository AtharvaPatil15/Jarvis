"""
Start the FastAPI backend server with voice controller support.
"""
from pathlib import Path
import sys

import uvicorn


APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main():
    print("Starting JARVIS backend server...")
    print("WebSocket: ws://localhost:8000/ws")
    uvicorn.run("jarvis_backend.server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
