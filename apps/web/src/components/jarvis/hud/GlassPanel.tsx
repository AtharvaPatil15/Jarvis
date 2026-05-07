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
        border border-cyan-400/30
        rounded-lg
        p-4
        shadow-lg
        shadow-cyan-400/10
        ${className}
      `}
      style={{
        boxShadow: '0 0 20px rgba(0, 255, 255, 0.3)',
      }}
    >
      {children}
    </div>
  );
}
