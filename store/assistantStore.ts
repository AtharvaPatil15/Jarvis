// store/assistantStore.ts
import { create } from 'zustand';

export type AssistantStatus = 'idle' | 'listening' | 'thinking' | 'responding' | 'executing_tool';

interface AssistantState {
  status: AssistantStatus;
  setStatus: (status: AssistantStatus) => void;
  transcript: string;
  setTranscript: (text: string) => void;
  activeTool: string | null;
  setActiveTool: (tool: string | null) => void;
}

export const useAssistantStore = create<AssistantState>((set) => ({
  status: 'idle',
  setStatus: (status) => set({ status }),
  transcript: "Waiting for command...",
  setTranscript: (transcript) => set({ transcript }),
  activeTool: null,
  setActiveTool: (activeTool) => set({ activeTool }),
}));
