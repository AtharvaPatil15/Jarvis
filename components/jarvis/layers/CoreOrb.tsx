"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { coreVertex, coreFragment } from "../shaders/coreOrbShader";
import { useVisualState } from "../visualState";

export default function CoreOrb() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const intensity = useVisualState((s) => s.intensity);

  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uIntensity: { value: 0.5 }
      },
      vertexShader: coreVertex,
      fragmentShader: coreFragment
    });
  }, []);

  useFrame(({ clock }) => {
    if (!material) return;

    material.uniforms.uTime.value = clock.elapsedTime;
    material.uniforms.uIntensity.value = intensity;
  });

  return (
    <mesh>
      <sphereGeometry args={[1.1, 128, 128]} />
      <primitive object={material} attach="material" />
    </mesh>
  );
}
