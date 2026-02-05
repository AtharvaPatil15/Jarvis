'use client';

import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { EffectComposer, Bloom, Noise, Vignette } from '@react-three/postprocessing';
import { CoreSphere } from '@/components/ai-core/CoreSphere';
import { ParticleField } from '@/components/ai-core/ParticleField';
import { BeamNetwork } from '@/components/ai-core/BeamNetwork';
import { AssistantText } from '@/components/overlay/AssistantText';
import { ToolIndicator } from '@/components/overlay/ToolIndicator';
import { useSocket } from '@/hooks/useSocket';

function SceneContent() {
  return (
    <>
      {/* Background color removed - CSS handles transparency */}
      
      <CoreSphere />
      <ParticleField />
      <BeamNetwork />
      
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#00A3FF" />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#FF0055" />

      <EffectComposer enableNormalPass={false}>
        <Bloom luminanceThreshold={0.2} mipmapBlur intensity={1.5} radius={0.4} />
        <Noise opacity={0.05} />
        <Vignette eskil={false} offset={0.1} darkness={1.1} />
      </EffectComposer>
    </>
  );
}

export default function Home() {
  useSocket(); 

  return (
    // ✅ FIX: Ensure parent div is transparent
    <div className="w-full h-screen bg-transparent relative overflow-hidden">
        <div className="absolute inset-0 z-0">
            <Canvas 
                camera={{ position: [0, 0, 8], fov: 45 }}
                // ✅ FIX: Enable alpha for transparency, antialias for clean edges
                gl={{ alpha: true, antialias: true }}
            >
                <Suspense fallback={null}>
                    <SceneContent />
                </Suspense>
            </Canvas>
        </div>

        <AssistantText />
        <ToolIndicator />
        
        <div className="absolute top-8 left-8 z-10 pointer-events-none">
            <h1 className="text-white font-bold text-xl tracking-[0.3em]">
              JARVIS<span className="text-cyan-400">.UI</span>
            </h1>
            <div className="h-0.5 w-12 bg-cyan-400 mt-2" />
        </div>
    </div>
  );
}