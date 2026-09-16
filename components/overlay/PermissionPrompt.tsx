'use client';

import { useAssistantStore } from '@/store/assistantStore';

export interface PermissionPromptProps {
  onRespond: (id: string, allowed: boolean) => void;
}

export function PermissionPrompt({ onRespond }: PermissionPromptProps) {
  const request = useAssistantStore((state) => state.pendingPermission);
  const setPendingPermission = useAssistantStore((state) => state.setPendingPermission);
  if (!request) return null;

  const answer = (allowed: boolean) => {
    onRespond(request.id, allowed);
    setPendingPermission(null);
  };

  return (
    <div
      role="alertdialog"
      aria-labelledby="permission-title"
      aria-describedby="permission-summary"
      className="absolute inset-x-6 top-1/3 z-30 rounded-lg border border-amber-500/60 bg-black/85 p-4 font-mono text-amber-100 shadow-lg"
    >
      <p id="permission-title" className="text-xs uppercase tracking-widest text-amber-400">
        Permission needed · {request.tool}
      </p>
      <p id="permission-summary" className="mt-2 text-sm">Allow JARVIS to {request.summary}?</p>
      <div className="mt-4 flex gap-3">
        <button type="button" onClick={() => answer(true)}
          className="rounded border border-amber-400 px-4 py-1.5 text-sm text-amber-100 hover:bg-amber-500/20 focus:outline-none focus:ring-2 focus:ring-amber-400">
          Allow
        </button>
        <button type="button" onClick={() => answer(false)}
          className="rounded border border-amber-500/40 px-4 py-1.5 text-sm text-amber-200/80 hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-amber-400">
          Deny
        </button>
      </div>
    </div>
  );
}