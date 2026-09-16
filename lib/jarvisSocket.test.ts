import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { JarvisSocket, type WebSocketLike } from './jarvisSocket';

class FakeSocket implements WebSocketLike {
  static instances: FakeSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: ((ev: unknown) => void) | null = null;
  onclose: ((ev: unknown) => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;
  constructor(public url: string) { FakeSocket.instances.push(this); }
  send(data: string) { this.sent.push(data); }
  close() { this.readyState = 3; this.onclose?.({}); }
  open() { this.readyState = 1; this.onopen?.({}); }
  receive(data: string) { this.onmessage?.({ data }); }
}

function make() {
  const events: unknown[] = [];
  const connection: boolean[] = [];
  const socket = new JarvisSocket({
    url: 'ws://test/ws',
    onEvent: (e) => events.push(e),
    onConnectionChange: (c) => connection.push(c),
    factory: (url) => new FakeSocket(url),
    baseDelayMs: 500,
    maxDelayMs: 2000,
  });
  return { socket, events, connection };
}

beforeEach(() => { FakeSocket.instances = []; vi.useFakeTimers(); });
afterEach(() => vi.useRealTimers());

describe('JarvisSocket', () => {
  it('reports connection, forwards parsed events and ignores malformed messages', () => {
    const { socket, events, connection } = make();
    socket.connect();
    FakeSocket.instances[0].open();
    FakeSocket.instances[0].receive('{"type":"ai_response","payload":"hi"}');
    FakeSocket.instances[0].receive('not json');
    expect(connection).toEqual([true]);
    expect(events).toEqual([{ type: 'ai_response', payload: 'hi' }]);
  });

  it('queues messages until the socket opens, then flushes them in order', () => {
    const { socket } = make();
    socket.connect();
    socket.sendUserText('  first  ');
    socket.respondToPermission('p1', true);
    expect(FakeSocket.instances[0].sent).toEqual([]);
    FakeSocket.instances[0].open();
    expect(FakeSocket.instances[0].sent).toEqual([
      '{"type":"user_text","payload":"first"}',
      '{"type":"permission_response","payload":{"id":"p1","allowed":true}}',
    ]);
  });

  it('ignores blank text', () => {
    const { socket } = make();
    expect(socket.sendUserText('   ')).toBe(false);
  });

  it('reconnects with exponential back-off capped at maxDelayMs', () => {
    const { socket, connection } = make();
    socket.connect();
    FakeSocket.instances[0].close();
    vi.advanceTimersByTime(499);
    expect(FakeSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.instances).toHaveLength(2);
    FakeSocket.instances[1].close();
    vi.advanceTimersByTime(1000);
    expect(FakeSocket.instances).toHaveLength(3);
    FakeSocket.instances[2].close();
    vi.advanceTimersByTime(2000);
    expect(FakeSocket.instances).toHaveLength(4);
    FakeSocket.instances[3].open();
    FakeSocket.instances[3].close();
    vi.advanceTimersByTime(500);
    expect(FakeSocket.instances).toHaveLength(5);
    expect(connection).toEqual([false, false, false, true, false]);
  });

  it('stops reconnecting after close()', () => {
    const { socket } = make();
    socket.connect();
    socket.close();
    vi.advanceTimersByTime(10_000);
    expect(FakeSocket.instances).toHaveLength(1);
  });
});