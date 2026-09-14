"""Start the JARVIS backend with settings from assistant/config.py."""
import uvicorn

from assistant.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("server:create_app", factory=True, host=settings.server_host, port=settings.server_port)