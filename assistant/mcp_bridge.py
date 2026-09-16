"""Starts the MCP servers in mcp_servers.json on a private event loop and exposes their tools to the agent."""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import re
import shutil
import sys
import threading
from collections.abc import Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from assistant.tools.base import BaseTool

log = logging.getLogger("jarvis.mcp")
CALL_TIMEOUT_S = 60.0
START_TIMEOUT_S = 90.0


@dataclass(frozen=True)
class ServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    requires_permission: bool = True


def load_config(path: Path) -> list[ServerConfig]:
    path = Path(path)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log.error("invalid MCP config %s: %s", path, exc)
        return []
    servers: list[ServerConfig] = []
    for name, entry in (data.get("servers") or {}).items():
        if not isinstance(entry, dict) or not entry.get("command"):
            log.error("MCP server %r has no command; skipped", name)
            continue
        servers.append(ServerConfig(name=name, command=str(entry["command"]),
                                    args=[str(a) for a in entry.get("args", [])], env=entry.get("env"),
                                    requires_permission=bool(entry.get("requires_permission", True))))
    return servers


def tool_name(server: str, tool: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", f"mcp__{server}__{tool}")[:64]


def resolve_command(command: str) -> str:
    if sys.platform == "win32":
        return shutil.which(command) or shutil.which(f"{command}.cmd") or command
    return command


def format_result(result: Any) -> str:
    parts = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        parts.append(text if text is not None else f"[{getattr(item, 'type', 'content')} omitted]")
    body = "\n".join(parts).strip() or "(no output)"
    return f"ERROR: {body}" if getattr(result, "isError", False) else body


class RawArgs(BaseModel):
    model_config = ConfigDict(extra="allow")


class MCPTool(BaseTool):
    Args = RawArgs

    def __init__(self, name: str, description: str, input_schema: dict[str, Any] | None,
                 caller: Callable[[dict[str, Any]], Any], requires_permission: bool) -> None:
        self.name = name
        self.description = description or "Tool provided by an MCP server."
        self.requires_permission = requires_permission
        self._schema = dict(input_schema) if input_schema else {}
        self._caller = caller

    def parameters(self) -> dict[str, Any]:
        schema = dict(self._schema)
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        return schema

    def parse_args(self, raw: dict[str, Any] | None) -> BaseModel:
        return RawArgs.model_validate(raw or {})

    def run(self, args: BaseModel) -> str:
        try:
            return format_result(self._caller(args.model_dump()))
        except Exception as exc:
            return f"ERROR: {self.name} failed: {exc}"


class MCPBridge:
    def __init__(self, config_path: Path) -> None:
        self._config_path = Path(config_path)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._main: concurrent.futures.Future[None] | None = None
        self._stop_event: asyncio.Event | None = None

    def start(self) -> list[BaseTool]:
        servers = load_config(self._config_path)
        if not servers:
            return []
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="mcp-bridge", daemon=True)
        self._thread.start()
        ready: concurrent.futures.Future[list[BaseTool]] = concurrent.futures.Future()
        self._main = asyncio.run_coroutine_threadsafe(self._serve(servers, ready), self._loop)
        return ready.result(timeout=START_TIMEOUT_S)

    def stop(self) -> None:
        if self._loop is None:
            return
        if self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._main is not None:
            try:
                self._main.result(timeout=15)
            except Exception:
                log.warning("MCP bridge did not shut down cleanly", exc_info=True)
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._loop, self._thread, self._main, self._stop_event = None, None, None, None

    async def _serve(self, servers: list[ServerConfig], ready: concurrent.futures.Future) -> None:
        """Enters and exits every server context inside this one task (required by the SDK's task groups)."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self._stop_event = asyncio.Event()
        try:
            async with AsyncExitStack() as stack:
                tools: list[BaseTool] = []
                for server in servers:
                    try:
                        params = StdioServerParameters(command=resolve_command(server.command), args=server.args,
                                                       env=server.env)
                        read, write = await stack.enter_async_context(stdio_client(params))
                        session = await stack.enter_async_context(ClientSession(read, write))
                        await asyncio.wait_for(session.initialize(), timeout=START_TIMEOUT_S)
                        listing = await session.list_tools()
                    except Exception as exc:
                        log.error("MCP server %s failed to start: %s", server.name, exc)
                        continue
                    for tool in listing.tools:
                        tools.append(MCPTool(tool_name(server.name, tool.name), tool.description or "",
                                             tool.inputSchema if hasattr(tool, 'inputSchema') else tool.input_schema,
                                             self._caller(session, tool.name),
                                             server.requires_permission))
                    log.info("MCP server %s: %d tools", server.name, len(listing.tools))
                ready.set_result(tools)
                await self._stop_event.wait()
        except BaseException as exc:
            if not ready.done():
                ready.set_exception(exc if isinstance(exc, Exception) else RuntimeError(str(exc)))
            else:
                log.warning("MCP bridge stopped with an error: %s", exc)

    def _caller(self, session: Any, name: str) -> Callable[[dict[str, Any]], Any]:
        def call(arguments: dict[str, Any]) -> Any:
            assert self._loop is not None
            return asyncio.run_coroutine_threadsafe(session.call_tool(name, arguments), self._loop).result(
                timeout=CALL_TIMEOUT_S)

        return call