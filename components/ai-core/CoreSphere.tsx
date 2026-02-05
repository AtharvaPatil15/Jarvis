// components/ai-core/CoreSphere.tsx
'use client';

import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Mesh, Color } from 'three';
import { useAssistantStore } from '@/store/assistantStore';
import { MathUtils } from 'three';
import * as THREE from 'three';

export const CoreSphere = () => {
  const meshRef = useRef<Mesh>(null);
  const innerRef = useRef<Mesh>(null);
  const status = useAssistantStore((state) => state.status);
  
  // Base colors for states
  const colors = {
    idle: new Color('#00A3FF'),      // Electric Blue
    listening: new Color('#00FF94'), // Mint Green
    thinking: new Color('#AE00FF'),  // Purple
    responding: new Color('#00A3FF'), // Blue
    executing_tool: new Color('#FF2E00') // Red
  };

  useFrame((state, delta) => {
    if (!meshRef.current || !innerRef.current) return;

    const t = state.clock.elapsedTime;
    const targetColor = colors[status] || colors.idle;

    // Smoothly interpolate color
    // @ts-ignore
    meshRef.current.material.color.lerp(targetColor, 0.05);
    // @ts-ignore
    innerRef.current.material.color.lerp(targetColor, 0.05);

    // STATE MACHINE ANIMATIONS
    switch (status) {
      case 'idle':
        // Slow breathing
        const breathe = Math.sin(t * 1) * 0.05 + 1;
        meshRef.current.scale.setScalar(breathe);
        meshRef.current.rotation.y += delta * 0.2;
        break;
        
      case 'listening':
        // Expansion
        meshRef.current.scale.lerp(new THREE.Vector3(1.2, 1.2, 1.2), 0.1);
        meshRef.current.rotation.y += delta * 0.5;
        break;
        
      case 'thinking':
        // Rapid chaotic rotation
        meshRef.current.rotation.x += delta * 2;
        meshRef.current.rotation.y += delta * 3;
        meshRef.current.scale.setScalar(1 + Math.sin(t * 10) * 0.05);
        break;
        
      case 'executing_tool':
        // Sharp pulsing
        const pulse = Math.sin(t * 20) > 0 ? 1.3 : 1.0;
        meshRef.current.scale.lerp(new THREE.Vector3(pulse, pulse, pulse), 0.2);
        break;
        
      default:
        meshRef.current.rotation.y += delta * 0.5;
    }
    
    // Inner core counter-rotation
    innerRef.current.rotation.y -= delta * 0.5;
    innerRef.current.rotation.z += delta * 0.2;
  });

  return (
    <group>
      {/* Outer Wireframe Shell */}
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.5, 2]} />
        <meshBasicMaterial 
          wireframe 
          transparent 
          opacity={0.3} 
          toneMapped={false} 
        />
      </mesh>

      {/* Inner Energy Core */}
      <mesh ref={innerRef} scale={[0.8, 0.8, 0.8]}>
        <icosahedronGeometry args={[1.5, 4]} />
        <meshBasicMaterial 
          transparent 
          opacity={0.8} 
          wireframe={true}
          wireframeLinewidth={2}
          toneMapped={false}
        />
      </mesh>
      
      {/* Solid Inner Glow Core */}
      <mesh scale={[0.5, 0.5, 0.5]}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial color="white" transparent opacity={0.5} />
      </mesh>
    </group>
  );
};
