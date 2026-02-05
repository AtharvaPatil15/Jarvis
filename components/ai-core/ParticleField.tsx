'use client';

import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { InstancedMesh, Object3D, AdditiveBlending } from 'three'; 
import { useAssistantStore } from '@/store/assistantStore';

const COUNT = 2000;

export const ParticleField = () => {
  const meshRef = useRef<InstancedMesh>(null);
  const status = useAssistantStore((state) => state.status);
  
  const dummy = useMemo(() => new Object3D(), []);
  
  const particles = useMemo(() => {
    const temp = [];
    for (let i = 0; i < COUNT; i++) {
      const t = Math.random() * 100;
      const factor = 20 + Math.random() * 100;
      const speed = 0.01 + Math.random() / 200;
      const xFactor = -50 + Math.random() * 100;
      const yFactor = -50 + Math.random() * 100;
      const zFactor = -50 + Math.random() * 100;
      temp.push({ t, factor, speed, xFactor, yFactor, zFactor });
    }
    return temp;
  }, []);

  useFrame((state) => {
    // 🛑 SAFETY CHECK: Prevent Crash if mesh isn't ready
    const mesh = meshRef.current;
    if (!mesh) return;

    const t = state.clock.getElapsedTime();
    const isThinking = status === 'thinking';
    const isExecuting = status === 'executing_tool';

    particles.forEach((particle, i) => {
      let { speed, xFactor, yFactor, zFactor } = particle;

      if (isThinking) {
         const radius = 10 + Math.random() * 5;
         dummy.position.set(
            Math.cos(t * speed * 10 + i) * radius,
            Math.sin(t * speed * 10 + i) * radius,
            (i % 20) - 10 
         );
      } else if (isExecuting) {
          dummy.position.set(
            xFactor + Math.sin(i) * 5,
            yFactor + Math.cos(i) * 5,
            zFactor + Math.sin(t) * 2
          );
      } else {
        dummy.position.set(
            xFactor + Math.cos((t * speed) + i) * 5,
            yFactor + Math.sin((t * speed) + i) * 5,
            zFactor
        );
      }

      dummy.rotation.set(
          Math.sin(t * 1.2), 
          Math.cos(t * 1.3), 
          Math.sin(t * 1.1)
      );
      
      const scale = (Math.sin(t * 2 + i) + 2) * 0.05;
      dummy.scale.setScalar(scale);

      dummy.updateMatrix();
      
      // ✅ USE LOCAL VARIABLE
      mesh.setMatrixAt(i, dummy.matrix);
    });

    // ✅ USE LOCAL VARIABLE
    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    // FIX: Reverted to undefined to satisfy TypeScript.
    // The safety check in useFrame handles the runtime crash.
    <instancedMesh ref={meshRef} args={[undefined, undefined, COUNT]}>
      <dodecahedronGeometry args={[0.2, 0]} />
      <meshBasicMaterial 
        color="#00A3FF" 
        transparent 
        opacity={0.4} 
        blending={AdditiveBlending}
        toneMapped={false}
      />
    </instancedMesh>
  );
};