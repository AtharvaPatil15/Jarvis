export const neuralGraphVertex = `
varying float vProgress;
varying vec2 vUv;

void main() {
  vUv = uv;
  vProgress = uv.x;

  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const neuralGraphFragment = `
uniform float uTime;
uniform float uIntensity;
uniform float uBaseTraffic;
uniform float uBurst;
uniform vec3  uColor;

varying float vProgress;

float band(float x, float center, float width) {
  return smoothstep(center - width, center, x) *
         (1.0 - smoothstep(center, center + width, x));
}

void main() {
  // ⭐ Continuous background traffic
  float baseCenter = fract(uTime * 0.05);
  float basePulse  = band(vProgress, baseCenter, 0.12) * uBaseTraffic;

  // ⭐ Burst pulse (faster, brighter)
  float burstCenter = fract(uTime * 0.25);
  float burstPulse  = band(vProgress, burstCenter, 0.08) * uBurst;

  float glow = basePulse + burstPulse;
  glow *= uIntensity;

  vec3 color = uColor * glow;

  gl_FragColor = vec4(color, glow);
}
`;
