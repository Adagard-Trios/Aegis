"use client";

/**
 * Vest deep-dive canvas. Same SSR-isolation reason as HeroCanvas —
 * dynamically imported so WebGL-dependent drei utilities never run on
 * the server.
 */
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import { VestModel3D } from "./VestModel3D";

// Sparkles dropped — see HeroCanvas.tsx note on the drei/Three 0.183
// incompatibility.

export default function VestSectionCanvas() {
  return (
    <Canvas camera={{ position: [0, 0.4, 4.2], fov: 40 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.5} />
      <pointLight position={[5, 5, 5]} intensity={1.2} color="#a855f7" />
      <pointLight position={[-5, -3, -3]} intensity={0.6} color="#d946ef" />
      <VestModel3D />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.6}
        target={[0, 0.3, 0]}
      />
      <Environment preset="city" />
    </Canvas>
  );
}
