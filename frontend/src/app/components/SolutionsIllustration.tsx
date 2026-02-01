"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef, useMemo } from "react";
import * as THREE from "three";

interface SolutionsIllustrationProps {
    activeTab: number;
}

// Color palette based on tab index
const TAB_COLORS = [
    "#56ab91", // Teal-500 - Operations Teams
    "#14b8a6", // Teal-500 alt - Business Analysts
    "#0d9488", // Teal-600 - Creators & Writers
    "#115e59", // Teal-800 - Project Managers
];

// Core floating sphere with orbiting elements
function TechCore({ activeTab }: { activeTab: number }) {
    const coreRef = useRef<THREE.Mesh>(null);
    const orbitRef = useRef<THREE.Group>(null);

    const coreColor = useMemo(() => TAB_COLORS[activeTab] || TAB_COLORS[0], [activeTab]);

    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        if (coreRef.current) {
            // Gentle float
            coreRef.current.position.y = Math.sin(t * 0.6) * 0.1;
            coreRef.current.rotation.y = t * 0.15;
        }
        if (orbitRef.current) {
            // Orbiting elements
            orbitRef.current.rotation.y = t * 0.3;
            orbitRef.current.rotation.z = t * 0.1;
        }
    });

    return (
        <group>
            {/* Main core sphere */}
            <mesh ref={coreRef} position={[0, 0, 0]}>
                <sphereGeometry args={[0.5, 32, 32]} />
                <meshStandardMaterial
                    color={coreColor}
                    roughness={0.2}
                    metalness={0.5}
                    emissive={coreColor}
                    emissiveIntensity={0.2}
                />
            </mesh>

            {/* Orbiting ring */}
            <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
                <torusGeometry args={[0.75, 0.02, 16, 100]} />
                <meshStandardMaterial color="#99e2b4" transparent opacity={0.6} />
            </mesh>

            {/* Orbiting elements */}
            <group ref={orbitRef}>
                {[0, 1, 2, 3].map((i) => (
                    <mesh
                        key={i}
                        position={[
                            Math.cos((i * Math.PI) / 2) * 0.75,
                            0,
                            Math.sin((i * Math.PI) / 2) * 0.75,
                        ]}
                    >
                        <boxGeometry args={[0.08, 0.08, 0.08]} />
                        <meshStandardMaterial color="#d8f3dc" emissive="#56ab91" emissiveIntensity={0.3} />
                    </mesh>
                ))}
            </group>

            {/* Base platform */}
            <mesh position={[0, -0.6, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <cylinderGeometry args={[0.6, 0.7, 0.1, 32]} />
                <meshStandardMaterial color="#f0fdf4" roughness={0.8} />
            </mesh>
        </group>
    );
}

export default function SolutionsIllustration({ activeTab }: SolutionsIllustrationProps) {
    return (
        <div className="w-full h-[300px] md:h-[350px]">
            <Canvas camera={{ position: [0, 0.5, 2.5], fov: 45 }}>
                {/* Lighting */}
                <ambientLight intensity={0.6} />
                <directionalLight position={[5, 5, 5]} intensity={0.8} color="#ffffff" />
                <directionalLight position={[-3, 2, -3]} intensity={0.3} color="#56ab91" />

                {/* Main 3D object */}
                <TechCore activeTab={activeTab} />
            </Canvas>
        </div>
    );
}
