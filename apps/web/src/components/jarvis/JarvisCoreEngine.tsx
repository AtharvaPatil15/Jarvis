'use client';

import { useEffect, useRef, useCallback } from 'react';
import CoreOrb from './layers/CoreOrb';
import { EnergyShell } from './layers/EnergyShell';
import NeuralGraphLayer from './layers/NeuralGraphLayer';
import { ConsciousParticles } from './layers/ConsciousParticles';

import { useVisualState, VisualState } from './visualState';
import { useAssistantStore } from '@/store/assistantStore';
import { useAudioAnalyzer } from '@/hooks/useAudioAnalyzer';

export default function JarvisCoreEngine() {
  const setState = useVisualState((s) => s.setState);
  const setIntensity = useVisualState((s) => s.setIntensity);
  const status = useAssistantStore((s) => s.status);
  const { getAmplitude, isReady } = useAudioAnalyzer();
  
  // Use refs to avoid re-renders from changing function identities
  const setIntensityRef = useRef(setIntensity);
  const getAmplitudeRef = useRef(getAmplitude);
  const isReadyRef = useRef(isReady);
  const rafRef = useRef<number | null>(null);
  const prevIntensityRef = useRef(0.5);
  
  // Keep refs up to date
  useEffect(() => {
    setIntensityRef.current = setIntensity;
    getAmplitudeRef.current = getAmplitude;
    isReadyRef.current = isReady;
  });

  // 🔹 Sync assistant state → visual state
  useEffect(() => {
    switch (status) {
      case 'idle':
        setState('idle');
        break;
      case 'listening':
        setState('listening');
        break;
      case 'thinking':
        setState('thinking');
        break;
      case 'responding':
        setState('speaking');
        break;
      case 'executing_tool':
        setState('executing');
        break;
    }
  }, [status, setState]);

  // 🔹 Voice amplitude → visual intensity (runs once on mount)
  useEffect(() => {
    const loop = () => {
      if (!isReadyRef.current) {
        // Keep looping but don't update if not ready
        rafRef.current = requestAnimationFrame(loop);
        return;
      }

      try {
        const amp = getAmplitudeRef.current();
        const mapped = 0.3 + amp * 0.9;
        
        // Only update if change is significant
        if (Math.abs(mapped - prevIntensityRef.current) > 0.02) {
          setIntensityRef.current(mapped);
          prevIntensityRef.current = mapped;
        }
      } catch {
        // Silently fail
      }

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []); // Empty deps - runs once on mount

  return (
    <>
      <CoreOrb />
      <EnergyShell />
      <NeuralGraphLayer />
      <ConsciousParticles />
    </>
  );
}

export function DebugControls() {
  const { setState, setIntensity } = useVisualState();

  const debugStates: { label: string; state: VisualState }[] = [
    { label: 'Idle', state: 'idle' },
    { label: 'Listening', state: 'listening' },
    { label: 'Thinking', state: 'thinking' },
    { label: 'Speaking', state: 'speaking' },
    { label: 'Executing', state: 'executing' },
  ];

  return (
    <div className="absolute bottom-8 right-8 z-30 pointer-events-auto">
      <div className="backdrop-blur-md bg-black/40 border border-cyan-400/30 rounded-lg p-4 space-y-3">
        <div className="text-xs text-cyan-300/70 font-mono mb-2">DEV CONTROLS</div>
        
        <div className="flex flex-wrap gap-2">
          {debugStates.map(({ label, state }) => (
            <button
              key={state}
              onClick={() => setState(state)}
              className="px-3 py-1.5 text-xs font-mono bg-cyan-900/30 hover:bg-cyan-700/50 
                        text-cyan-400 border border-cyan-400/30 rounded transition-all
                        hover:shadow-lg hover:shadow-cyan-400/20"
            >
              {label}
            </button>
          ))}
        </div>
        
        <div className="pt-2 border-t border-cyan-400/20">
          <label htmlFor="intensity-slider" className="text-xs text-cyan-300/70 font-mono block mb-2">
            INTENSITY
          </label>
          <input
            id="intensity-slider"
            type="range"
            min="0"
            max="1"
            step="0.05"
            defaultValue="0.5"
            onChange={(e) => setIntensity(parseFloat(e.target.value))}
            className="w-full accent-cyan-400"
          />
        </div>
      </div>
    </div>
  );
}
