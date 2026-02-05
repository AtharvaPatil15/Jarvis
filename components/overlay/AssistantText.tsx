// components/overlay/AssistantText.tsx
'use client';

import { motion } from 'framer-motion';
import { useAssistantStore } from '@/store/assistantStore';

export const AssistantText = () => {
  const transcript = useAssistantStore((state) => state.transcript);
  const status = useAssistantStore((state) => state.status);

  return (
    <div className="absolute bottom-20 left-0 right-0 flex justify-center pointer-events-none z-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        key={transcript}
        className="bg-black/40 backdrop-blur-md border border-white/10 px-8 py-4 rounded-full"
      >
        <p className="text-cyan-200 font-mono text-sm tracking-widest uppercase mb-1">
            System Status: <span className="text-white">{status}</span>
        </p>
        <p className="text-white text-lg font-light text-center">
          {transcript}
        </p>
      </motion.div>
    </div>
  );
};
