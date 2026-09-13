'use client';

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useVisualState } from '../visualState';

export default function OrbitalRings() {
  const ringsRef = useRef<THREE.Group>(null);
  const { state } = useVisualState();

  const rings = [
    { radius: 2.4, tilt: 0, speed: 0.004 },
    { radius: 2.5, tilt: Math.PI / 3, speed: -0.005 },
    { radius: 2.5, tilt: Math.PI / 2, speed: 0.003 },
    { radius: 2.6, tilt: (Math.PI * 2) / 3, speed: -0.006 },
    { radius: 2.7, tilt: Math.PI / 5, speed: 0.007 },
    { radius: 2.4, tilt: (Math.PI * 4) / 5, speed: -0.004 },
  ];

  const ringRefs = useRef(rings.map(() => new THREE.Object3D()));

  useFrame(() => {
    const multiplier = state === 'listening' || state === 'thinking' ? 2.0 : 1.0;

    ringRefs.current.forEach((obj, i) => {
      obj.rotation.z += rings[i].speed * multiplier;
    });

    if (ringsRef.current) {
      ringsRef.current.children.forEach((child, i) => {
        child.rotation.z = ringRefs.current[i].rotation.z;
      });
    }
  });

  return (
    <group ref={ringsRef}>
      {rings.map((ring, i) => (
        <mesh key={i} rotation={[ring.tilt, 0, 0]}>
          <torusGeometry args={[ring.radius, 0.006, 8, 200]} />
          <meshBasicMaterial
            color="#ffb000"
            transparent
            opacity={0.55}
            toneMapped={false}
          />
        </mesh>
      ))}
    </group>
  );
}
