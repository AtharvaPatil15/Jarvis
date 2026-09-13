'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useVisualState } from '../visualState';
import { neuralGraphVertex, neuralGraphFragment } from '../shaders/neuralGraphShader';

export default function NeuralGraphLayer() {
  const lineSegmentsRef = useRef<THREE.LineSegments>(null);
  const { state, intensity } = useVisualState();

  const { geometry } = useMemo(() => {
    const SPHERE_RADIUS = 2.0;
    const nodeCount = 600;
    const connectionThreshold = 0.85;
    const nodes: THREE.Vector3[] = [];

    for (let i = 0; i < nodeCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      nodes.push(
        new THREE.Vector3(
          SPHERE_RADIUS * Math.sin(phi) * Math.cos(theta),
          SPHERE_RADIUS * Math.sin(phi) * Math.sin(theta),
          SPHERE_RADIUS * Math.cos(phi)
        )
      );
    }

    for (let lat = 1; lat < 9; lat++) {
      const phi = (Math.PI * lat) / 9;
      const count = 10;
      for (let lng = 0; lng < count; lng++) {
        const theta = (Math.PI * 2 * lng) / count;
        nodes.push(
          new THREE.Vector3(
            SPHERE_RADIUS * Math.sin(phi) * Math.cos(theta),
            SPHERE_RADIUS * Math.sin(phi) * Math.sin(theta),
            SPHERE_RADIUS * Math.cos(phi)
          )
        );
      }
    }

    const connections: number[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (nodes[i].distanceTo(nodes[j]) < connectionThreshold) {
          connections.push(
            nodes[i].x, nodes[i].y, nodes[i].z,
            nodes[j].x, nodes[j].y, nodes[j].z
          );
        }
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(connections), 3));

    const segmentCount = connections.length / 6;
    const uvs = new Float32Array(segmentCount * 4);
    for (let i = 0; i < segmentCount; i++) {
      uvs[i * 4] = 0;
      uvs[i * 4 + 1] = 0;
      uvs[i * 4 + 2] = 1;
      uvs[i * 4 + 3] = 0;
    }
    geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));

    return { geometry };
  }, []);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: {
          uTime: { value: 0 },
          uIntensity: { value: 0.5 },
          uBaseTraffic: { value: 0.4 },
          uBurst: { value: 0.0 },
          uColor: { value: new THREE.Color('#ffb000') },
        },
        vertexShader: neuralGraphVertex,
        fragmentShader: neuralGraphFragment,
      }),
    []
  );

  useFrame((frameState) => {
    if (lineSegmentsRef.current) {
      lineSegmentsRef.current.rotation.y = frameState.clock.elapsedTime * 0.06;
      lineSegmentsRef.current.rotation.x = Math.sin(frameState.clock.elapsedTime * 0.2) * 0.1;
    }

    material.uniforms.uTime.value = frameState.clock.elapsedTime;
    material.uniforms.uIntensity.value = intensity;

    let burst = 0.0;
    if (state === 'listening') burst = 0.4;
    if (state === 'thinking') burst = 0.7;
    if (state === 'speaking') burst = 1.0;
    if (state === 'executing') burst = 1.0;
    material.uniforms.uBurst.value = burst;
  });

  return (
    <lineSegments ref={lineSegmentsRef} geometry={geometry} material={material} />
  );
}
