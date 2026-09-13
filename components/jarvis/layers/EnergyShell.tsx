'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { energyVertex, energyFragment } from '../shaders/energyShellShader';
import { useVisualState } from '../visualState';

export function EnergyShell() {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const { intensity } = useVisualState();

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime;
      materialRef.current.uniforms.uIntensity.value = intensity;
    }
    
    // Slow rotation
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.001;
      meshRef.current.rotation.x += 0.0005;
    }
  });

  return (
    <mesh ref={meshRef} scale={1.8}>
      <icosahedronGeometry args={[1, 4]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={energyVertex}
        fragmentShader={energyFragment}
        uniforms={{
          uTime: { value: 0 },
          uIntensity: { value: intensity },
        }}
        transparent
        blending={THREE.AdditiveBlending}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}
