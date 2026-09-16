import json
from types import SimpleNamespace

from assistant.mcp_bridge import MCPBridge, MCPTool, format_result, load_config, tool_name


def test_config_loading(tmp_path) -> None:
    assert load_config(tmp_path / "missing.json") == []
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_config(bad) == []
    good = tmp_path / "mcp.json"
    good.write_text(json.dumps({"servers": {
        "fs": {"command": "npx", "args": ["-y", "pkg", "3"]},
        "safe": {"command": "python", "requires_permission": False},
        "broken": {"args": ["x"]},
    }}), encoding="utf-8")
    servers = load_config(good)
    assert [(s.name, s.command, s.args, s.requires_permission) for s in servers] == [
        ("fs", "npx", ["-y", "pkg", "3"], True), ("safe", "python", [], False)]


def test_tool_names_are_namespaced_sanitised_and_bounded() -> None:
    assert tool_name("filesystem", "read_text_file") == "mcp__filesystem__read_text_file"
    assert tool_name("my server", "do.thing") == "mcp__my_server__do_thing"
    assert len(tool_name("s", "x" * 100)) == 64


def test_results_are_formatted_as_text() -> None:
    text = SimpleNamespace(type="text", text="hello")
    image = SimpleNamespace(type="image")
    assert format_result(SimpleNamespace(content=[text, image], isError=False)) == "hello\n[image omitted]"
    assert format_result(SimpleNamespace(content=[text], isError=True)) == "ERROR: hello"
    assert format_result(SimpleNamespace(content=[], isError=False)) == "(no output)"


def test_mcp_tool_schema_arguments_and_errors() -> None:
    calls: list[dict] = []
    schema = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}

    def caller(arguments: dict):
        calls.append(arguments)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="file body")], isError=False)

    tool = MCPTool("mcp__fs__read", "Read a file", schema, caller, requires_permission=True)
    assert tool.schema()["function"] == {"name": "mcp__fs__read", "description": "Read a file", "parameters": schema}
    assert tool.requires_permission is True
    assert tool.run(tool.parse_args({"path": "C:/x.txt"})) == "file body"
    assert calls == [{"path": "C:/x.txt"}]

    def failing(arguments: dict):
        raise TimeoutError("server hung")

    broken = MCPTool("mcp__fs__read", "", None, failing, requires_permission=False)
    assert broken.parameters() == {"type": "object", "properties": {}}
    assert broken.run(broken.parse_args({})) == "ERROR: mcp__fs__read failed: server hung"


def test_bridge_with_no_servers_starts_nothing(tmp_path) -> None:
    bridge = MCPBridge(tmp_path / "missing.json")
    assert bridge.start() == []
    bridge.stop()