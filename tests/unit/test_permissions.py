import asyncio

from assistant.safety.permissions import AllowAllGate, DenyAllGate, WebSocketPermissionGate


async def test_static_gates() -> None:
    assert await AllowAllGate().request("x", "y") is True
    assert await DenyAllGate().request("x", "y") is False


async def test_websocket_gate_emits_request_and_waits_for_approval(events) -> None:
    gate = WebSocketPermissionGate(events, timeout_s=5)
    task = asyncio.create_task(gate.request("read_file", "read notes.txt"))
    await asyncio.sleep(0.01)
    (payload,) = events.payloads("permission_request")
    assert payload["tool"] == "read_file" and payload["summary"] == "read notes.txt" and payload["id"]
    gate.resolve(payload["id"], True)
    assert await task is True


async def test_websocket_gate_denial(events) -> None:
    gate = WebSocketPermissionGate(events, timeout_s=5)
    task = asyncio.create_task(gate.request("read_file", "read notes.txt"))
    await asyncio.sleep(0.01)
    gate.resolve(events.payloads("permission_request")[0]["id"], False)
    assert await task is False


async def test_resolution_from_another_thread(events) -> None:
    gate = WebSocketPermissionGate(events, timeout_s=5)
    task = asyncio.create_task(gate.request("open_app", "open notepad"))
    await asyncio.sleep(0.01)
    await asyncio.to_thread(gate.resolve, events.payloads("permission_request")[0]["id"], True)
    assert await task is True


async def test_timeout_denies_and_late_answers_are_ignored(events) -> None:
    gate = WebSocketPermissionGate(events, timeout_s=0.05)
    assert await gate.request("x", "y") is False
    gate.resolve(events.payloads("permission_request")[0]["id"], True)


def test_resolving_an_unknown_id_is_ignored(events) -> None:
    WebSocketPermissionGate(events).resolve("does-not-exist", True)