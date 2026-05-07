export const energyVertex = `
  uniform float uTime;
  uniform float uIntensity;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    vUv = uv;
    vNormal = normalize(normalMatrix * normal);
    vPosition = position;
    
    // Time-based displacement for energy flow
    vec3 pos = position;
    float wave = sin(length(pos) * 2.0 - uTime * 3.0) * 0.15 * uIntensity;
    wave += cos(pos.y * 4.0 + uTime * 2.0) * 0.1 * uIntensity;
    
    pos += normal * wave;
    
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

export const energyFragment = `
  uniform float uTime;
  uniform float uIntensity;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    // Transparent energy color
    vec3 energyColor = vec3(0.0, 0.8, 1.0);
    
    // Fresnel for edge glow
    vec3 viewDirection = normalize(cameraPosition - vPosition);
    float fresnel = pow(1.0 - abs(dot(viewDirection, vNormal)), 3.0);
    
    // Flowing energy pattern
    float flow = sin(vPosition.y * 5.0 + uTime * 4.0) * 0.5 + 0.5;
    flow *= sin(vPosition.x * 3.0 - uTime * 3.0) * 0.5 + 0.5;
    
    // Additive energy appearance
    float energy = fresnel * uIntensity * flow;
    vec3 color = energyColor * energy;
    
    // Transparent with additive blending
    float alpha = energy * 0.4;
    
    gl_FragColor = vec4(color, alpha);
  }
`;
