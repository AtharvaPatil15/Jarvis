import type { AssistantStatus, PermissionRequest } from '@/store/assistantStore';

export const ASSISTANT_STATUSES: readonly AssistantStatus[] = [
  'idle',
  'listening',
  'thinking',
  'responding',
  'executing_tool',
];

export interface SocketActions {
  setStatus: (status: AssistantStatus) => void;
  setTranscript: (text: string) => void;
  setActiveTool: (tool: string | null) => void;
  appendResponseDelta: (delta: string) => void;
  endStream: () => void;
  setPendingPermission: (request: PermissionRequest | null) => void;
}

export interface ServerEvent {
  type: string;
  payload: unknown;
}

export function isAssistantStatus(value: unknown): value is AssistantStatus {
  return typeof value === 'string' && (ASSISTANT_STATUSES as readonly string[]).includes(value);
}

function field(payload: unknown, key: string): unknown {
  return payload !== null && typeof payload === 'object' ? (payload as Record<string, unknown>)[key] : undefined;
}

function isPermissionRequest(payload: unknown): payload is PermissionRequest {
  return ['id', 'tool', 'summary'].every((key) => typeof field(payload, key) === 'string');
}

export function applyServerEvent(event: ServerEvent, actions: SocketActions): boolean {
  const { type, payload } = event;
  switch (type) {
    case 'state_change':
      if (!isAssistantStatus(payload)) return false;
      if (payload === 'thinking') actions.endStream();
      if (payload === 'idle') actions.setPendingPermission(null);
      actions.setStatus(payload);
      return true;
    case 'wake_word_detected':
      actions.setStatus('listening');
      return true;
    case 'user_transcript':
      if (typeof payload !== 'string') return false;
      actions.endStream();
      actions.setTranscript(`"${payload}"`);
      return true;
    case 'ai_response_delta':
      if (typeof payload !== 'string') return false;
      actions.appendResponseDelta(payload);
      return true;
    case 'ai_response':
      if (typeof payload !== 'string') return false;
      actions.setTranscript(payload);
      actions.endStream();
      return true;
    case 'tool_start': {
      const name = field(payload, 'name');
      if (typeof name !== 'string') return false;
      actions.setActiveTool(name);
      return true;
    }
    case 'tool_end':
      actions.setActiveTool(null);
      actions.setPendingPermission(null);
      return true;
    case 'permission_request':
      if (!isPermissionRequest(payload)) return false;
      actions.setPendingPermission({ id: payload.id, tool: payload.tool, summary: payload.summary });
      return true;
    case 'reminder': {
      const text = field(payload, 'text');
      if (typeof text !== 'string') return false;
      actions.setTranscript(`Reminder: ${text}`);
      return true;
    }
    case 'error': {
      const message = field(payload, 'message');
      actions.setTranscript(`Error: ${typeof message === 'string' ? message : 'unknown error'}`);
      return true;
    }
    default:
      return false;
  }
}