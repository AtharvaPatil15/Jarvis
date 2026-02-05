// hooks/useAudioAnalyzer.ts
import { useRef, useEffect } from 'react';
import * as Tone from 'tone';

export const useAudioAnalyzer = () => {
  const analyzerRef = useRef<Tone.Analyser | null>(null);
  const dataArray = useRef<Float32Array>(new Float32Array(32));
  const isRunning = useRef(false);

  useEffect(() => {
    const startAudio = async () => {
      // Create a dummy oscillator for "idle" hum simulation if no mic
      // In a real app, you would swap this with Tone.UserMedia()
      const osc = new Tone.Oscillator(50, "sine").toDestination();
      const noise = new Tone.Noise("pink").start();
      const filter = new Tone.Filter(100, "lowpass").toDestination();
      
      noise.connect(filter);
      
      // We'll simulate input for this visual demo
      // In production: const mic = new Tone.UserMedia(); await mic.open();
      
      const analyser = new Tone.Analyser("fft", 32);
      analyzerRef.current = analyser;
      
      // Connect simulation to analyzer (Volume low to not blast speakers)
      osc.connect(analyser); 
      osc.volume.value = -Infinity; // Silent but data flows
      osc.start();

      isRunning.current = true;
    };

    startAudio();

    return () => {
      // Cleanup
      isRunning.current = false;
    };
  }, []);

  const getAudioData = () => {
    if (analyzerRef.current) {
      const values = analyzerRef.current.getValue();
      // Tone.js returns Float32Array in dB usually, we normalize for visualizer
      // Simulating normalized 0-1 data for the UI
      return Math.random() * 0.5; // Mocking return for purely visual demo stability
    }
    return 0;
  };

  return { getAudioData };
};
