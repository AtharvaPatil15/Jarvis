import type { ServerEvent } from './socketEvents';

export interface WebSocketLike {
  readyState: number;
  onopen: ((ev: unknown) => void) | null;
  onclose: ((ev: unknown) => void) | null;
  onmessage: ((ev: { data: string }) => void) | null;
  onerror: ((ev: unknown) => void) | null;
  send(data: string): void;
  close(): void;
}

export interface JarvisSocketOptions {
  url: string;
  onEvent: (event: ServerEvent) => void;
  onConnectionChange: (connected: boolean) => void;
  factory?: (url: string) => WebSocketLike;
  baseDelayMs?: number;
  maxDelayMs?: number;
}

const OPEN = 1;
const MAX_QUEUE = 50;

export class JarvisSocket {
  private socket: WebSocketLike | null = null;
  private attempts = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private closedByUser = false;
  private queue: string[] = [];

  constructor(private readonly options: JarvisSocketOptions) {}

  connect(): void {
    this.closedByUser = false;
    const factory = this.options.factory ?? ((url: string) => new WebSocket(url) as unknown as WebSocketLike);
    const socket = factory(this.options.url);
    this.socket = socket;
    socket.onopen = () => {
      this.attempts = 0;
      this.options.onConnectionChange(true);
      for (const message of this.queue.splice(0)) socket.send(message);
    };
    socket.onmessage = (event) => {
      try {
        this.options.onEvent(JSON.parse(event.data) as ServerEvent);
      } catch {
        // Malformed frames are ignored; the server only sends JSON.
      }
    };
    socket.onclose = () => {
      if (this.socket === socket) this.socket = null;
      this.options.onConnectionChange(false);
      if (!this.closedByUser) this.scheduleReconnect();
    };
    socket.onerror = () => socket.close();
  }

  send(type: string, payload: unknown): void {
    const message = JSON.stringify({ type, payload });
    if (this.socket && this.socket.readyState === OPEN) {
      this.socket.send(message);
    } else if (this.queue.length < MAX_QUEUE) {
      this.queue.push(message);
    }
  }

  sendUserText(text: string): boolean {
    const trimmed = text.trim();
    if (!trimmed) return false;
    this.send('user_text', trimmed);
    return true;
  }

  respondToPermission(id: string, allowed: boolean): void {
    this.send('permission_response', { id, allowed });
  }

  close(): void {
    this.closedByUser = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.socket?.close();
    this.socket = null;
  }

  private scheduleReconnect(): void {
    const base = this.options.baseDelayMs ?? 500;
    const max = this.options.maxDelayMs ?? 8000;
    const delay = Math.min(max, base * 2 ** this.attempts);
    this.attempts += 1;
    this.timer = setTimeout(() => this.connect(), delay);
  }
}