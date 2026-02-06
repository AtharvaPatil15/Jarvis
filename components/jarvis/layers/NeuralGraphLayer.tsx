'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useVisualState } from '../visualState';
import { neuralGraphVertex, neuralGraphFragment } from '../shaders/neuralGraphShader';

export default function NeuralGraphLayer() {
  const lineSegmentsRef = useRef<THREE.LineSegments>(null);
  const { state, intensity } = useVisualState();

  // Generate nodes and connections ONCE using useMemo
  const { geometry } = useMemo(() => {
    const nodeCount = 300;
    const nodes: THREE.Vector3[] = [];
    const connectionThreshold = 1.8;
    const sphereRadius = 2.2;

    // Generate node positions in spherical volume
    for (let i = 0; i < nodeCount; i++) {
      const direction = new THREE.Vector3()
        .randomDirection()
        .multiplyScalar(sphereRadius * Math.random());
      nodes.push(direction);
    }

    // Calculate connections based on distance threshold
    const connections: number[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const distance = nodes[i].distanceTo(nodes[j]);
        if (distance < connectionThreshold) {
          // Add line segment vertices
          connections.push(
            nodes[i].x, nodes[i].y, nodes[i].z,
            nodes[j].x, nodes[j].y, nodes[j].z
          );
        }
      }
    }

    // Create BufferGeometry with positions
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(connections);
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    // Attach UV coordinates for shader animation
    // Each line segment (2 vertices) gets UVs: (0,0) and (1,0)
    const segmentCount = connections.length / 3 / 2;
    const uvs = new Float32Array(segmentCount * 2 * 2); // 2 vertices per segment, 2 components per UV
    for (let i = 0; i < segmentCount; i++) {
      uvs[i * 4] = 0;     // start vertex u
      uvs[i * 4 + 1] = 0; // start vertex v
      uvs[i * 4 + 2] = 1; // end vertex u
      uvs[i * 4 + 3] = 0; // end vertex v
    }
    geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));

    return { geometry, nodeCount };
  }, []);

  // Create shader material ONCE using useMemo
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uIntensity: { value: 0.5 },
        uBaseTraffic: { value: 0.25 },
        uBurst: { value: 0.0 },
        uColor: { value: new THREE.Color('#00ccff') },
      },
      vertexShader: neuralGraphVertex,
      fragmentShader: neuralGraphFragment,
    });
  }, []);

  // Animate transforms and uniforms
  useFrame((frameState) => {
    if (lineSegmentsRef.current) {
      // Slow Y-axis rotation
      lineSegmentsRef.current.rotation.y = frameState.clock.elapsedTime * 0.08;
      
      // Subtle X oscillation
      lineSegmentsRef.current.rotation.x = Math.sin(frameState.clock.elapsedTime * 0.3) * 0.15;
    }

    // Update shader uniforms
    material.uniforms.uTime.value = frameState.clock.elapsedTime;
    material.uniforms.uIntensity.value = intensity;
    material.uniforms.uBaseTraffic.value = 0.25;

    // State-driven burst mapping
    let burst = 0.0;
    if (state === 'listening') burst = 0.35;
    if (state === 'thinking') burst = 0.6;
    if (state === 'speaking') burst = 0.9;
    if (state === 'executing') burst = 1.0;
    
    material.uniforms.uBurst.value = burst;
  });

  return (
    <lineSegments ref={lineSegmentsRef} geometry={geometry} material={material} />
  );
}
