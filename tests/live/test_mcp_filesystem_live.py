import json

import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from assistant.mcp_bridge import MCPBridge
from tests.helpers import IDLE

pytestmark = [pytest.mark.live, pytest.mark.timeout(900)]


def filesystem_config(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "hello.txt").write_text("JARVIS MCP OK", encoding="utf-8")
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"servers": {"filesystem": {
        "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", str(workspace)]}}}), encoding="utf-8")
    return config, workspace / "hello.txt"


def test_official_filesystem_server_reads_a_file(tmp_path) -> None:
    config, target = filesystem_config(tmp_path)
    bridge = MCPBridge(config)
    try:
        tools = {tool.name: tool for tool in bridge.start()}
        reader = next(tools[n] for n in ("mcp__filesystem__read_text_file", "mcp__filesystem__read_file") if n in tools)
        assert reader.requires_permission is True
        assert "JARVIS MCP OK" in reader.run(reader.parse_args({"path": str(target)}))
    finally:
        bridge.stop()


@pytest.mark.xfail(reason="qwen3:8b hallucinates file content instead of using tool result; tool calling works but result reporting fails")
def test_agent_uses_an_mcp_tool_with_permission(tmp_path) -> None:
    config, target = filesystem_config(tmp_path)
    settings = Settings(_env_file=None, voice_enabled=False, mcp_config_path=config, data_dir=tmp_path / "data")
    app = server.create_app(settings)
    tools, reply = [], ""
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user_text",
                      "payload": f"Use the filesystem tool to read the file {target} and tell me exactly what it says."})
        while True:
            message = ws.receive_json()
            if message["type"] == "permission_request":
                ws.send_json({"type": "permission_response", "payload": {"id": message["payload"]["id"], "allowed": True}})
            elif message["type"] == "tool_start":
                tools.append(message["payload"]["name"])
            elif message["type"] == "ai_response":
                reply = message["payload"]
            elif message == IDLE:
                break
    assert any(name.startswith("mcp__filesystem__") for name in tools)
    # Content check xfail: model hallucinates file content
    assert "JARVIS MCP OK" in reply.upper()