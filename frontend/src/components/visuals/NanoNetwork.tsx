'use client'
import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, Sphere, MeshDistortMaterial, Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'

function AnimatedNodes() {
  const points = useMemo(() => {
    const p = new Float32Array(500 * 3)
    for (let i = 0; i < 500; i++) {
      p[i * 3] = (Math.random() - 0.5) * 15
      p[i * 3 + 1] = (Math.random() - 0.5) * 15
      p[i * 3 + 2] = (Math.random() - 0.5) * 15
    }
    return p
  }, [])

  const ref = useRef<any>(null)
  
  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.x = state.clock.getElapsedTime() * 0.05
      ref.current.rotation.y = state.clock.getElapsedTime() * 0.03
    }
  })

  return (
    <group ref={ref}>
      <Points positions={points} stride={3} frustumCulled={false}>
        <PointMaterial
          transparent
          color="#6366f1"
          size={0.05}
          sizeAttenuation={true}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </Points>
    </group>
  )
}

function FloatingOrb() {
  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={2}>
      <Sphere args={[1.5, 64, 64]}>
        <MeshDistortMaterial
          color="#4f46e5"
          speed={3}
          distort={0.4}
          radius={1}
          emissive="#2d00ff"
          emissiveIntensity={0.5}
        />
      </Sphere>
    </Float>
  )
}

export function NanoNetwork() {
  return (
    <div className="absolute inset-0 -z-10 bg-slate-950">
      <Canvas camera={{ position: [0, 0, 10], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1.5} color="#8b5cf6" />
        <pointLight position={[-10, -10, -10]} intensity={1} color="#3b82f6" />
        <AnimatedNodes />
        <FloatingOrb />
      </Canvas>
      {/* Grain Overlay */}
      <div className="absolute inset-0 opacity-10 pointer-events-none mix-blend-overlay bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
    </div>
  )
}
