'use client';

import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Mesh, Color, Vector3 } from 'three';
import { useAssistantStore } from '@/store/assistantStore';
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

    // --- 3️⃣ Base Scale Control ---
    const baseScale = 0.9;
    let targetScale = baseScale;

    // STATE MACHINE ANIMATIONS
    switch (status) {
      case 'idle':
        targetScale = baseScale + Math.sin(t * 1) * 0.05;
        meshRef.current.rotation.y += delta * 0.2;
        break;

      case 'listening':
        targetScale = baseScale * 1.1;
        meshRef.current.rotation.y += delta * 0.5;
        break;

      case 'thinking':
        meshRef.current.rotation.x += delta * 2;
        meshRef.current.rotation.y += delta * 3;
        targetScale = baseScale + Math.sin(t * 8) * 0.06;
        break;

      case 'executing_tool':
        targetScale = baseScale * 1.2;
        break;

      default:
        meshRef.current.rotation.y += delta * 0.3;
    }

    // Apply smooth scaling
    meshRef.current.scale.lerp(
      new THREE.Vector3(targetScale, targetScale, targetScale),
      0.08
    );
    
    // Inner core counter-rotation
    innerRef.current.rotation.y -= delta * 0.5;
    innerRef.current.rotation.z += delta * 0.2;
  });

  return (
    <group>
      {/* Outer Wireframe Shell */}
      <mesh ref={meshRef}>
        {/* 1️⃣ Reduced Outer Size */}
        <icosahedronGeometry args={[0.9, 2]} />
        <meshBasicMaterial 
          wireframe 
          transparent 
          opacity={0.3} 
          toneMapped={false} 
        />
      </mesh>

      {/* Inner Energy Core */}
      <mesh ref={innerRef} scale={[0.8, 0.8, 0.8]}>
        {/* 1️⃣ Reduced Inner Size */}
        <icosahedronGeometry args={[0.6, 4]} />
        <meshBasicMaterial 
          transparent 
          opacity={0.5} 
          wireframe={true}
          wireframeLinewidth={2}
          toneMapped={false}
        />
      </mesh>
      
      {/* 2️⃣ REMOVED Solid Inner Glow Core to fix "Giant Blob" look */}
    </group>
  );
};