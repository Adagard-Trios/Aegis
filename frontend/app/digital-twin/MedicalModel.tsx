import React, { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import { TelemetryData } from '../hooks/useVestStream';
import * as THREE from 'three';

interface MedicalModelProps {
  data: TelemetryData | null;
  simulationMode?: string;
}

export default function MedicalModel({ data, simulationMode = 'Live' }: MedicalModelProps) {
  const { scene } = useGLTF('/human.glb');
  
  // References to our hierarchical meshes
  const torsoRef = useRef<THREE.Group>(null);
  const heartRef = useRef<THREE.Mesh>(null);
  const wombRef = useRef<THREE.Mesh>(null);
  const fetalCoreRef = useRef<THREE.Mesh>(null);

  // We use useFrame to smoothly interpolate (lerp) values 60 times a second
  useFrame((state) => {
    if (!torsoRef.current || !data) return;

    // 1. Posture Binding (Smoothly lean the torso)
    const targetPitch = (data.imu?.upper_roll || 0) * (Math.PI / 180); // Pitch maps to lateral for visual translation
    const targetRoll = (data.imu?.spinal_angle || 0) * (Math.PI / 180);
    
    torsoRef.current.rotation.x = THREE.MathUtils.lerp(torsoRef.current.rotation.x, targetRoll, 0.1);
    torsoRef.current.rotation.z = THREE.MathUtils.lerp(torsoRef.current.rotation.z, targetPitch, 0.1);

    // 2. Maternal Heatmap Binding
    let tempC = data.temperature?.cervical || 0;
    const tNorm = Math.max(0, Math.min(1, (tempC - 36.0) / 2.0));
    const targetColor = new THREE.Color().setHSL(0.6 - (tNorm * 0.6), 1.0, 0.5); // Blue to Red

    scene.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (mesh.isMesh) {
        if (!mesh.userData.customMaterialApplied) {
          mesh.material = new THREE.MeshPhysicalMaterial({
            color: targetColor,
            transparent: true,
            opacity: 0.4,
            roughness: 0.2,
            transmission: 0.8,
            wireframe: false
          });
          mesh.userData.customMaterialApplied = true;
        } else {
          (mesh.material as THREE.MeshPhysicalMaterial).color.lerp(targetColor, 0.05);
        }
      }
    });

    // 3. Maternal Heartbeat Pulse
    if (heartRef.current) {
        const time = state.clock.getElapsedTime();
        const bpm = data.vitals?.heart_rate > 0 ? data.vitals.heart_rate : 72;
        const pulse = 1.0 + Math.sin(time * (bpm / 60) * Math.PI * 2) * 0.15;
        heartRef.current.scale.lerp(new THREE.Vector3(pulse, pulse, pulse), 0.2);
    }

    // 4. Uterine Contractions & Fetal Kicks & Long-Term Gestational Scaling
    if (wombRef.current) {
        // Evaluate Fetal State
        const hasKicks = data.fetal?.kicks?.some(k => k) || false;
        const hasContractions = data.fetal?.contractions?.some(c => c) || false;

        // Long-term gestational scaling overrides
        let gestationScaleFactor = 1.0;
        if (simulationMode === '2w') gestationScaleFactor = 1.15;
        if (simulationMode === '4w') gestationScaleFactor = 1.45;

        // Contraction -> Increase womb scale and flush red
        const activeTarget = hasContractions ? 1.15 : 1.0;
        const finalWombScale = activeTarget * gestationScaleFactor;
        wombRef.current.scale.lerp(new THREE.Vector3(finalWombScale, finalWombScale, finalWombScale), 0.05);
        
        const wombMat = wombRef.current.material as THREE.MeshPhysicalMaterial;
        const targetWombColor = hasContractions ? new THREE.Color(0xff3333) : new THREE.Color(0x3388ff);
        wombMat.color.lerp(targetWombColor, 0.1);
        wombMat.emissive.lerp(hasContractions ? new THREE.Color(0x880000) : new THREE.Color(0x001133), 0.1);

        // Kicks -> Physical Jitter / Displacing the womb mesh
        if (hasKicks) {
            wombRef.current.position.x = THREE.MathUtils.randFloatSpread(0.2);
            wombRef.current.position.z = THREE.MathUtils.randFloatSpread(0.2);
        } else {
            // Settle back to original anchor (which is [0, 0.7, 0.12])
            wombRef.current.position.x = THREE.MathUtils.lerp(wombRef.current.position.x, 0, 0.1);
            wombRef.current.position.z = THREE.MathUtils.lerp(wombRef.current.position.z, 0.12, 0.1);
        }
    }

    // 5. Fetal Heartbeat Pulse
    if (fetalCoreRef.current) {
        const time = state.clock.getElapsedTime();
        // Fetal HR is generally double maternal, using 145 internal baseline + jitter
        const hasKicks = data.fetal?.kicks?.some(k => k) || false;
        const fhr = hasKicks ? 155 : 140; 
        const pulse = 1.0 + Math.sin(time * (fhr / 60) * Math.PI * 2) * 0.2;
        fetalCoreRef.current.scale.lerp(new THREE.Vector3(pulse, pulse, pulse), 0.2);
    }
  });

  return (
    <group position={[0, -1, 0]}>
      {/* Dynamic Torso Group (Pivots from the base) */}
      <group ref={torsoRef} position={[0, -0.8, 0]} scale={[1.8, 1.8, 1.8]}>
        
        {/* Render the realistic human model */}
        <primitive object={scene} />

        {/* Maternal Heart */}
        <mesh ref={heartRef} position={[-0.1, 1.15, 0.05]}>
          <sphereGeometry args={[0.08, 16, 16]} />
          <meshStandardMaterial color="#ff2244" emissive="#ff0022" emissiveIntensity={2} toneMapped={false} />
        </mesh>

        {/* Womb / Fetal Environment */}
        <mesh ref={wombRef} position={[0, 0.7, 0.12]}>
          <sphereGeometry args={[0.25, 32, 32]} />
          <meshPhysicalMaterial 
            color="#3388ff" 
            emissive="#001133"
            transparent={true} 
            opacity={0.5} 
            roughness={0.2}
            clearcoat={1.0}
            clearcoatRoughness={0.1}
            transmission={0.9}
            thickness={1.5}
            ior={1.5}
          />
          
          {/* Fetal Core Inside Womb */}
          <mesh ref={fetalCoreRef} position={[0, 0, 0.05]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshStandardMaterial color="#ffcc00" emissive="#ffaa00" emissiveIntensity={1.5} />
          </mesh>
        </mesh>
        
      </group>
      
      {/* Floor / Grid for perspective */}
      <gridHelper args={[10, 20, "#444444", "#222222"]} position={[0, 0, 0]} />
    </group>
  );
}
