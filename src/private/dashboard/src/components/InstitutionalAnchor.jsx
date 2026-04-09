import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { MeshWobbleMaterial, Sphere, Float } from '@react-three/drei';
import * as THREE from 'three';

const InstitutionalAnchor = ({ position, name, isVetted }) => {
  const meshRef = useRef();
  const shieldRef = useRef();

  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    if (shieldRef.current) {
      shieldRef.current.scale.setScalar(1.2 + Math.sin(time * 2) * 0.05);
      shieldRef.current.rotation.y += 0.01;
    }
  });

  return (
    <group position={position}>
      {/* The Anchor Pillar */}
      <mesh ref={meshRef}>
        <boxGeometry args={[0.5, 3, 0.5]} />
        <meshStandardMaterial 
          color={isVetted ? "#FFD700" : "#C0C0C0"} 
          metalness={1} 
          roughness={0.1} 
          emissive={"#FFD700"}
          emissiveIntensity={0.5}
        />
      </mesh>

      {/* The Epistemic Force Field */}
      <Sphere ref={shieldRef} args={[1, 32, 32]}>
        <meshBasicMaterial 
          color={isVetted ? "#4FD1C5" : "#718096"} 
          transparent 
          opacity={0.2} 
          wireframe
        />
      </Sphere>

      {/* Label (Floating) */}
      <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
        <mesh position={[0, 2, 0]}>
          <textGeometry args={[name, { size: 0.2, height: 0.05 }]} />
          <meshStandardMaterial color="white" />
        </mesh>
      </Float>
    </group>
  );
};

export default InstitutionalAnchor;
