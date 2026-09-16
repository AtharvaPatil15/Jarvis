// store/assistantStore.ts
import { create } from 'zustand';

export type AssistantStatus = 'idle' | 'listening' | 'thinking' | 'responding' | 'executing_tool';

export interface PermissionRequest {
  id: string;
  tool: string;
  summary: string;
}

interface AssistantState {
  status: AssistantStatus;
  setStatus: (status: AssistantStatus) => void;
  transcript: string;
  setTranscript: (text: string) => void;
  streaming: boolean;
  appendResponseDelta: (delta: string) => void;
  endStream: () => void;
  activeTool: string | null;
  setActiveTool: (tool: string | null) => void;
  connected: boolean;
  setConnected: (connected: boolean) => void;
  pendingPermission: PermissionRequest | null;
  setPendingPermission: (request: PermissionRequest | null) => void;
}

export const useAssistantStore = create<AssistantState>((set) => ({
  status: 'idle',
  setStatus: (status) => set({ status }),
  transcript: 'Waiting for command...',
  setTranscript: (transcript) => set({ transcript }),
  streaming: false,
  appendResponseDelta: (delta) =>
    set((state) => (state.streaming ? { transcript: state.transcript + delta } : { transcript: delta, streaming: true })),
  endStream: () => set({ streaming: false }),
  activeTool: null,
  setActiveTool: (activeTool) => set({ activeTool }),
  connected: false,
  setConnected: (connected) => set({ connected }),
  pendingPermission: null,
  setPendingPermission: (pendingPermission) => set({ pendingPermission }),
}));