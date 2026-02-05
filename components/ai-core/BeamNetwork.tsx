// components/ai-core/BeamNetwork.tsx
'use client';

import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Mesh } from 'three';
import { useAssistantStore } from '@/store/assistantStore';
import * as THREE from 'three';

export const BeamNetwork = () => {
  const ref = useRef<Mesh>(null);
  const status = useAssistantStore((state) => state.status);
  
  useFrame((state) => {
    if (!ref.current) return;
    
    // Only visible in specific states
    const targetOpacity = (status === 'executing_tool' || status === 'thinking') ? 0.5 : 0;
    
    // @ts-ignore
    ref.current.material.opacity = THREE.MathUtils.lerp(ref.current.material.opacity, targetOpacity, 0.1);
    
    ref.current.rotation.z += 0.02;
    ref.current.rotation.x = Math.PI / 2;
  });

  return (
    <mesh ref={ref}>
      <torusGeometry args={[3, 0.02, 16, 100]} />
      <meshBasicMaterial color="#FF2E00" transparent opacity={0} toneMapped={false} />
    </mesh>
  );
};
