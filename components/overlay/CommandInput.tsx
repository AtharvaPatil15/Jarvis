'use client';

import { useState, type FormEvent } from 'react';
import { useAssistantStore } from '@/store/assistantStore';

export interface CommandInputProps {
  onSend: (text: string) => boolean;
}

export function CommandInput({ onSend }: CommandInputProps) {
  const connected = useAssistantStore((state) => state.connected);
  const [text, setText] = useState('');

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (connected && onSend(text)) setText('');
  };

  return (
    <form onSubmit={submit} className="absolute bottom-6 left-1/2 z-20 w-[min(92vw,420px)] -translate-x-1/2">
      <input
        aria-label="Command"
        value={text}
        onChange={(event) => setText(event.target.value)}
        disabled={!connected}
        placeholder={connected ? 'Type a command and press Enter' : 'Connecting to JARVIS...'}
        className="w-full rounded-full border border-amber-500/40 bg-black/60 px-5 py-3 font-mono text-sm text-amber-100 outline-none placeholder:text-amber-200/40 focus:border-amber-400 disabled:opacity-50"
      />
    </form>
  );
}