import * as THREE from 'three';
import { shaderMaterial } from '@react-three/drei';
import { extend } from '@react-three/fiber';

const DistortionMaterial = shaderMaterial(
  {
    uTime: 0,
    uIntensity: 0.1,
    uResolution: new THREE.Vector2(),
    uMouse: new THREE.Vector2(),
    uSpikes: [new THREE.Vector4(0, 0, 0, 0)], // x, y, radius, force
    uCalms: [new THREE.Vector4(0, 0, 0, 0)], // x, y, radius, reduction_force
  },
  // Vertex Shader
  `
  varying vec2 vUv;
  varying float vElevation;
  uniform float uTime;
  uniform float uIntensity;
  uniform vec4 uSpikes[10];
  uniform vec4 uCalms[10];

  void main() {
    vUv = uv;
    vec3 pos = position;

    float elevation = 0.0;
    
    // Social Hysteria (Distortion)
    for(int i = 0; i < 10; i++) {
        float dist = distance(pos.xy, uSpikes[i].xy);
        float radius = uSpikes[i].z;
        float force = uSpikes[i].w;
        
        if(radius > 0.0) {
            float influence = 1.0 - smoothstep(0.0, radius, dist);
            elevation += sin(dist * 10.0 - uTime * 5.0) * influence * force * uIntensity;
        }
    }

    // Institutional Anchors (Calming Field)
    float stability = 0.0;
    for(int i = 0; i < 10; i++) {
        float dist = distance(pos.xy, uCalms[i].xy);
        float radius = uCalms[i].z;
        float force = uCalms[i].w;
        
        if(radius > 0.0) {
            float influence = 1.0 - smoothstep(0.0, radius, dist);
            stability += influence * force;
        }
    }

    elevation *= (1.0 - clamp(stability, 0.0, 1.0));
    pos.z += elevation * 2.0;

    vElevation = elevation;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
  `,
  // Fragment Shader
  `
  varying vec2 vUv;
  varying float vElevation;
  uniform float uTime;

  void main() {
    // Cyberpunk Grid Visuals
    float gridX = step(0.98, fract(vUv.x * 50.0));
    float gridY = step(0.98, fract(vUv.y * 50.0));
    float grid = max(gridX, gridY);

    vec3 baseColor = vec3(0.05, 0.05, 0.1); // Deep Navy
    vec3 hysteriaColor = vec3(0.9, 0.1, 0.1); // Volatile Red
    
    vec3 color = mix(baseColor, hysteriaColor, vElevation * 2.0);
    color += grid * vec3(0.1, 0.4, 0.8) * (1.0 + vElevation); // Blue grid glow

    gl_FragColor = vec4(color, 0.9);
  }
  `
);

extend({ DistortionMaterial });

export default DistortionMaterial;
