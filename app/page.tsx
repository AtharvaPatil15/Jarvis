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
      <color attach="background" args={['#050505']} />
      
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
  // ✅ Active Socket Connection
  useSocket(); 

  return (
    <div className="w-full h-screen bg-[#050505] relative overflow-hidden">
        <div className="absolute inset-0 z-0">
            <Canvas 
                camera={{ position: [0, 0, 8], fov: 45 }}
                dpr={[1, 2]} 
                // CRITICAL FIX: Removed 'depth: false' to fix rendering issues
                gl={{ antialias: false, stencil: false }}
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