"use client";

/**
 * Hero-section Three.js canvas, isolated so it can be dynamically imported
 * with ssr: false. R3F + drei pull WebGL-only modules (OrbitControls,
 * Environment HDR loader) that crash during static prerender on Vercel
 * with a "client-side exception" — keeping them out of the SSR graph
 * entirely is the standard fix.
 */
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, Stars, Sparkles } from "@react-three/drei";
import { VestModel3D } from "./VestModel3D";

export default function HeroCanvas() {
  return (
    <Canvas camera={{ position: [0, 0, 4.5], fov: 45 }}>
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={0.7} color="#a855f7" />
      <pointLight position={[-5, -3, -5]} intensity={0.4} color="#d946ef" />
      <Sparkles count={80} scale={8} size={1.5} speed={0.3} color="#a855f7" opacity={0.3} />
      <Stars radius={20} depth={50} count={500} factor={3} fade speed={0.5} />
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
