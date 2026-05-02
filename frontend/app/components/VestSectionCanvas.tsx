"use client";

/**
 * Vest deep-dive canvas. Same SSR-isolation reason as HeroCanvas —
 * dynamically imported so WebGL-dependent drei utilities never run on
 * the server.
 */
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import { VestScene } from "./VestModel3D";

// See HeroCanvas.tsx for why we use VestScene (the inner content) rather
// than VestModel3D (the DOM-wrapping component with its own Canvas).

export default function VestSectionCanvas() {
  return (
    <Canvas camera={{ position: [0, 0.12, 1.8], fov: 38 }} dpr={[1, 1.5]} gl={{ alpha: true, antialias: true }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[5, 5, 5]} intensity={1.2} color="#a855f7" />
      <pointLight position={[-5, -3, -3]} intensity={0.6} color="#d946ef" />
      <VestScene onSensorHover={() => { /* hover overlay is in the parent section */ }} />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.6}
        target={[0, 0.12, 0]}
      />
      <Environment preset="city" />
    </Canvas>
  );
}
