'use client';

import { useVisualState } from '../visualState';
import { GlassPanel } from './GlassPanel';

export function HolographicHUD() {
  const { state, intensity } = useVisualState();

  const stateColors: Record<string, string> = {
    idle: 'text-cyan-400',
    listening: 'text-green-400',
    thinking: 'text-purple-400',
    speaking: 'text-blue-400',
    executing: 'text-red-400',
  };

  const stateLabels: Record<string, string> = {
    idle: 'IDLE',
    listening: 'LISTENING',
    thinking: 'THINKING',
    speaking: 'SPEAKING',
    executing: 'EXECUTING',
  };

  return (
    <div className="absolute top-24 left-8 z-20 pointer-events-none">
      <GlassPanel>
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full ${stateColors[state]} animate-pulse`}
              style={{
                boxShadow: `0 0 10px currentColor`,
              }}
            />
            <span className={`font-mono text-sm font-bold ${stateColors[state]}`}>
              {stateLabels[state]}
            </span>
          </div>
          
          <div className="space-y-1">
            <div className="text-xs text-cyan-300/70 font-mono">INTENSITY</div>
            <div className="w-32 h-1 bg-cyan-900/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 transition-all duration-300"
                style={{ width: `${intensity * 100}%` }}
              />
            </div>
            <div className="text-xs text-cyan-400/80 font-mono">
              {(intensity * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </GlassPanel>
    </div>
  );
}
