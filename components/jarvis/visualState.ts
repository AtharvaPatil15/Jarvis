import { create } from 'zustand';

export type VisualState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'executing';

interface VisualStateStore {
  state: VisualState;
  intensity: number;
  setState: (state: VisualState) => void;
  setIntensity: (intensity: number) => void;
}

export const useVisualState = create<VisualStateStore>((set) => ({
  state: 'idle',
  intensity: 0.5,
  setState: (state) => set({ state }),
  setIntensity: (intensity) => set({ intensity }),
}));
