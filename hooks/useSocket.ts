'use client';

import { useEffect, useRef } from 'react';
import { useAssistantStore } from '@/store/assistantStore';

export const useSocket = () => {
  const setStatus = useAssistantStore((state) => state.setStatus);
  const setTranscript = useAssistantStore((state) => state.setTranscript);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // 1. Connect to the Python Brain
    const ws = new WebSocket('ws://localhost:8000/ws');
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('✅ Visuals Connected to Brain');
      setTranscript("Systems Online.");
    };

    ws.onclose = () => {
      console.log('❌ Visuals Disconnected');
      setTranscript("Connection Lost.");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const { type, payload } = data;
        
        console.log(`📩 Socket Event: ${type}`, payload);

        // 2. Route events to the Store (Global State)
        switch (type) {
          case 'state_change':
            // payload = 'idle' | 'listening' | 'thinking' | 'speaking' | 'executing_tool'
            setStatus(payload); 
            break;
            
          case 'user_transcript':
            setTranscript(`"${payload}"`);
            break;
            
          case 'ai_response':
            setTranscript(payload);
            break;
            
          case 'wake_word_detected':
            setStatus('listening');
            break;
        }
      } catch (e) {
        console.error('Socket Parse Error', e);
      }
    };

    return () => {
      if (ws.readyState === 1) ws.close();
    };
  }, [setStatus, setTranscript]);

  return socketRef.current;
};