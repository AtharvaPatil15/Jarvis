// components/overlay/ToolIndicator.tsx
'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useAssistantStore } from '@/store/assistantStore';

export const ToolIndicator = () => {
  const activeTool = useAssistantStore((state) => state.activeTool);
  const status = useAssistantStore((state) => state.status);

  const show = status === 'executing_tool' || activeTool;

  return (
    <AnimatePresence>
      {show && (
        <motion.div 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 50 }}
            className="absolute top-10 right-10 z-10"
        >
          <div className="bg-red-500/10 border border-red-500/50 p-4 rounded-lg w-64">
            <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-red-400 font-mono text-xs uppercase">Executing Process</span>
            </div>
            <p className="text-white font-mono text-sm">
                {activeTool || 'Initializing connection...'}
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
