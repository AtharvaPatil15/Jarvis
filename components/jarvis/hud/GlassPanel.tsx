'use client';

import { ReactNode } from 'react';

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
}

export function GlassPanel({ children, className = '' }: GlassPanelProps) {
  return (
    <div
      className={`
        backdrop-blur-md
        bg-black/20
        border border-amber-400/30
        rounded-lg
        p-4
        shadow-lg
        shadow-amber-400/10
        ${className}
      `}
      style={{
        boxShadow: '0 0 20px rgba(255, 176, 0, 0.3)',
      }}
    >
      {children}
    </div>
  );
}
