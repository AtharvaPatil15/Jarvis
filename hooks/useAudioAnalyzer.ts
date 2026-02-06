import { useRef, useEffect, useState } from 'react';

export const useAudioAnalyzer = () => {
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataRef = useRef<Uint8Array | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Only initialize in browser environment
    if (typeof window === 'undefined') return;

    const initMic = async () => {
      try {
        // Check if getUserMedia is available
        if (!navigator?.mediaDevices?.getUserMedia) {
          console.log("⚠️ Audio API not available");
          return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        const audioCtx = new AudioContext();
        const source = audioCtx.createMediaStreamSource(stream);

        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;

        source.connect(analyser);

        analyserRef.current = analyser;
        dataRef.current = new Uint8Array(new ArrayBuffer(analyser.frequencyBinCount));
        audioCtxRef.current = audioCtx;
        setIsReady(true);

        console.log("🎤 Audio Analyzer Ready");
      } catch (err) {
        console.log("⚠️ Mic access denied or unavailable");
      }
    };

    initMic();
  }, []);

  const getAmplitude = () => {
    if (!analyserRef.current || !dataRef.current || !isReady) return 0;

    try {
      // @ts-ignore - Web Audio API type definition mismatch
      analyserRef.current.getByteFrequencyData(dataRef.current);

      let sum = 0;
      for (let i = 0; i < dataRef.current.length; i++) {
        sum += dataRef.current[i];
      }

      return (sum / dataRef.current.length) / 255;
    } catch (err) {
      return 0;
    }
  };

  return { getAmplitude, isReady };
};
