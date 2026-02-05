# start_backend.py
"""
Starts the FastAPI backend server with voice controller.
Run this FIRST before launching the Electron UI.
"""
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting JARVIS Backend Server...")
    print("📡 WebSocket: ws://localhost:8000/ws")
    print("🎤 Voice Controller: Active")
    print("")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
