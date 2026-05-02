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
import { VestScene } from "./VestModel3D";

// VestModel3D ships its OWN <Canvas> + DOM tooltip wrapper — nesting it
// under another <Canvas> caused R3F to try to instantiate React DOM nodes
// as THREE primitives ("R3F: P is not part of the THREE namespace"). Use
// the inner <VestScene /> instead: it's the pure 3D content, designed to
// drop into any parent Canvas.

export default function HeroCanvas() {
  return (
    <Canvas camera={{ position: [0, 0.12, 1.8], fov: 38 }} dpr={[1, 1.5]} gl={{ alpha: true, antialias: true }}>
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={0.7} color="#a855f7" />
      <pointLight position={[-5, -3, -5]} intensity={0.4} color="#d946ef" />
      <VestScene onSensorHover={() => { /* no hover affordance on the marketing hero */ }} />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate
        autoRotateSpeed={0.4}
        target={[0, 0.12, 0]}
      />
      <Environment preset="city" />
    </Canvas>
  );
}
