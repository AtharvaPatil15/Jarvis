import asyncio

from assistant.events import AssistantState, EventType
from assistant.hub import ConnectionHub


class FakeSocket:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[dict] = []
        self.accepted = False
        self.fail = fail

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        if self.fail:
            raise RuntimeError("socket closed")
        self.sent.append(data)


async def _hub_with(*sockets: FakeSocket) -> ConnectionHub:
    hub = ConnectionHub()
    hub.bind_loop(asyncio.get_running_loop())
    for socket in sockets:
        await hub.connect(socket)
    return hub


async def test_messages_arrive_in_emit_order() -> None:
    ws = FakeSocket()
    hub = await _hub_with(ws)
    for i in range(25):
        hub.emit("state_change", str(i))
    await hub.drain()
    assert [m["payload"] for m in ws.sent] == [str(i) for i in range(25)]
    assert ws.accepted
    await hub.close()


async def test_emit_from_another_thread_is_delivered() -> None:
    ws = FakeSocket()
    hub = await _hub_with(ws)
    await asyncio.to_thread(hub.emit, "user_transcript", "hi")
    await hub.drain()
    assert ws.sent == [{"type": "user_transcript", "payload": "hi"}]
    await hub.close()


async def test_failing_socket_is_dropped_and_others_still_receive() -> None:
    good, bad = FakeSocket(), FakeSocket(fail=True)
    hub = await _hub_with(good, bad)
    await hub.broadcast("error", {"message": "x"})
    await hub.drain()
    assert hub.client_count == 1
    assert good.sent == [{"type": "error", "payload": {"message": "x"}}]
    await hub.close()


async def test_enums_are_sent_as_plain_strings() -> None:
    ws = FakeSocket()
    hub = await _hub_with(ws)
    hub.emit(EventType.STATE_CHANGE, AssistantState.THINKING)
    await hub.drain()
    assert ws.sent == [{"type": "state_change", "payload": "thinking"}]
    assert type(ws.sent[0]["type"]) is str and type(ws.sent[0]["payload"]) is str
    await hub.close()