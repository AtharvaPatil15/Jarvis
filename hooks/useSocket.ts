'use client';

import { useEffect, useRef } from 'react';
import { applyServerEvent } from '@/lib/socketEvents';
import { useAssistantStore } from '@/store/assistantStore';

const SOCKET_URL = process.env.NEXT_PUBLIC_JARVIS_WS_URL ?? 'ws://127.0.0.1:8000/ws';

export const useSocket = () => {
  const setStatus = useAssistantStore((state) => state.setStatus);
  const setTranscript = useAssistantStore((state) => state.setTranscript);
  const setActiveTool = useAssistantStore((state) => state.setActiveTool);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(SOCKET_URL);
    socketRef.current = ws;
    ws.onopen = () => setTranscript('Systems online.');
    ws.onclose = () => setTranscript('Connection lost.');
    ws.onmessage = (event) => {
      try {
        applyServerEvent(JSON.parse(event.data), { setStatus, setTranscript, setActiveTool });
      } catch {
        console.error('Invalid socket message', event.data);
      }
    };
    return () => ws.close();
  }, [setStatus, setTranscript, setActiveTool]);

  return socketRef;
};