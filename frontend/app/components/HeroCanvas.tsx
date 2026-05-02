"use client";

/**
 * Hero-section Three.js canvas, isolated so it can be dynamically imported
 * with ssr: false. R3F + drei pull WebGL-only modules (OrbitControls,
 * Environment HDR loader) that crash during static prerender on Vercel
 * with a "client-side exception" — keeping them out of the SSR graph
 * entirely is the standard fix.
 */
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment } from "@react-three/drei";
import { VestModel3D } from "./VestModel3D";

// drei's Sparkles + Stars rely on the deprecated THREE.Clock and crash
// under Three.js 0.183 with "R3F: P is not part of the THREE namespace".
// The vest + violet point-lights + Environment carry the visual weight
// on their own; particles are decorative and can come back when drei
// catches up to the new THREE.Timer API.

export default function HeroCanvas() {
  return (
    <Canvas camera={{ position: [0, 0, 4.5], fov: 45 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={0.7} color="#a855f7" />
      <pointLight position={[-5, -3, -5]} intensity={0.4} color="#d946ef" />
      <VestModel3D />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.4}
        target={[0, 0.3, 0]}
      />
      <Environment preset="city" />
    </Canvas>
  );
}
