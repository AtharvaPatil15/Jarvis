'use client';

import { useEffect } from 'react';
import { JarvisSocket } from '@/lib/jarvisSocket';
import { applyServerEvent } from '@/lib/socketEvents';
import { useAssistantStore } from '@/store/assistantStore';

const SOCKET_URL = process.env.NEXT_PUBLIC_JARVIS_WS_URL ?? 'ws://127.0.0.1:8000/ws';
let activeSocket: JarvisSocket | null = null;

export const getJarvisSocket = (): JarvisSocket | null => activeSocket;

export const useSocket = (): void => {
  useEffect(() => {
    const store = useAssistantStore.getState();
    const socket = new JarvisSocket({
      url: SOCKET_URL,
      onEvent: (event) => applyServerEvent(event, useAssistantStore.getState()),
      onConnectionChange: (connected) => {
        store.setConnected(connected);
        store.setTranscript(connected ? 'Systems online.' : 'Reconnecting to JARVIS...');
      },
    });
    activeSocket = socket;
    socket.connect();
    return () => {
      socket.close();
      if (activeSocket === socket) activeSocket = null;
    };
  }, []);
};