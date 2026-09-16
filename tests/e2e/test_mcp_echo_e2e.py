import json
import sys
from pathlib import Path

import pytest

from assistant.mcp_bridge import MCPBridge

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(180)]
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "echo_mcp_server.py"


def write_config(path: Path, servers: dict) -> Path:
    path.write_text(json.dumps({"servers": servers}), encoding="utf-8")
    return path


def test_bridge_exposes_and_calls_tools_from_a_real_server(tmp_path) -> None:
    config = write_config(tmp_path / "mcp.json", {
        "echo": {"command": sys.executable, "args": [str(FIXTURE)], "requires_permission": False}})
    bridge = MCPBridge(config)
    try:
        tools = {tool.name: tool for tool in bridge.start()}
        assert {"mcp__echo__echo", "mcp__echo__add"} <= set(tools)
        echo, add = tools["mcp__echo__echo"], tools["mcp__echo__add"]
        assert echo.parameters()["properties"]["text"]["type"] == "string"
        assert echo.run(echo.parse_args({"text": "JARVIS MCP OK"})) == "JARVIS MCP OK"
        assert add.run(add.parse_args({"a": 2, "b": 40})) == "42"
    finally:
        bridge.stop()


def test_a_broken_server_does_not_block_the_others(tmp_path) -> None:
    config = write_config(tmp_path / "mcp.json", {
        "ghost": {"command": "definitely-not-a-real-command-xyz"},
        "echo": {"command": sys.executable, "args": [str(FIXTURE)]}})
    bridge = MCPBridge(config)
    try:
        names = [tool.name for tool in bridge.start()]
        assert "mcp__echo__echo" in names and not any(n.startswith("mcp__ghost__") for n in names)
    finally:
        bridge.stop()


def test_server_registers_mcp_tools_at_startup(tmp_path) -> None:
    from fastapi.testclient import TestClient

    import server
    from assistant.config import Settings

    config = write_config(tmp_path / "mcp.json", {"echo": {"command": sys.executable, "args": [str(FIXTURE)]}})
    app = server.create_app(Settings(_env_file=None, llm_backend="fake", voice_enabled=False, mcp_config_path=config))
    with TestClient(app):
        assert "mcp__echo__echo" in app.state.registry.names()