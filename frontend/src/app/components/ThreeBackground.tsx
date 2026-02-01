"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Points, PointMaterial } from "@react-three/drei";
import { useState, useRef, useMemo } from "react";
import * as random from "maath/random/dist/maath-random.esm";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function FloatingParticles(props: any) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ref = useRef<any>(null);
  const [sphere] = useState(() => random.inSphere(new Float32Array(3000), { radius: 1.2 }));

  useFrame((state, delta) => {
    if (ref.current) {
      ref.current.rotation.x -= delta / 20;
      ref.current.rotation.y -= delta / 25;
    }
  });

  return (
    <group rotation={[0, 0, Math.PI / 6]}>
      <Points ref={ref} positions={sphere} stride={3} frustumCulled={false} {...props}>
        <PointMaterial
          transparent
          color="#56ab91" // Teal-400 from our palette
          size={0.003}
          sizeAttenuation={true}
          depthWrite={false}
          opacity={0.6}
        />
      </Points>
    </group>
  );
}

// Subtle ambient orbs for depth
function AmbientOrbs() {
  const orb1Ref = useRef<any>(null);
  const orb2Ref = useRef<any>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (orb1Ref.current) {
      orb1Ref.current.position.y = Math.sin(t * 0.3) * 0.2;
      orb1Ref.current.position.x = Math.cos(t * 0.2) * 0.1;
    }
    if (orb2Ref.current) {
      orb2Ref.current.position.y = Math.cos(t * 0.25) * 0.15;
      orb2Ref.current.position.x = Math.sin(t * 0.15) * 0.1;
    }
  });

  return (
    <>
      <mesh ref={orb1Ref} position={[-0.5, 0.3, 0]}>
        <sphereGeometry args={[0.15, 32, 32]} />
        <meshBasicMaterial color="#99e2b4" transparent opacity={0.15} />
      </mesh>
      <mesh ref={orb2Ref} position={[0.6, -0.2, 0]}>
        <sphereGeometry args={[0.1, 32, 32]} />
        <meshBasicMaterial color="#78c6a3" transparent opacity={0.12} />
      </mesh>
    </>
  );
}

export default function ThreeBackground() {
  return (
    <div className="absolute inset-0 z-0 opacity-30 pointer-events-none">
      <Canvas camera={{ position: [0, 0, 1] }}>
        <FloatingParticles />
        <AmbientOrbs />
      </Canvas>
    </div>
  );
}
