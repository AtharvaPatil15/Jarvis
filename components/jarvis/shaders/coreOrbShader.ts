export const coreVertex = `
uniform float uTime;
varying vec2 vUv;

void main() {

  vUv = uv;

  vec3 pos = position;

  // subtle organic breathing distortion
  pos += normal * sin(uTime + position.y * 4.0) * 0.05;

  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos,1.0);
}
`;

export const coreFragment = `
uniform float uTime;
uniform float uIntensity;

varying vec2 vUv;

void main() {

  vec2 center = vUv - 0.5;
  float dist = length(center);

  // radial glow falloff
  float glow = smoothstep(0.6, 0.15, dist);

  // breathing pulse
  float pulse = sin(uTime * 2.0) * 0.5 + 0.5;

  float alpha = glow * pulse * uIntensity;

  vec3 color = vec3(0.0, 0.85, 1.0) * alpha;

  gl_FragColor = vec4(color, alpha);
}
`;
