"use client";

import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows, Stars, Sparkles } from '@react-three/drei';
import MedicalModel from './MedicalModel';
import { useVestStream } from '../hooks/useVestStream';
import { PharmacologyPanel } from '../components/PharmacologyPanel';

export default function DigitalTwinPage() {
  const { data, connected, error } = useVestStream();

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100 overflow-hidden font-sans">
      
      {/* 3D Canvas Context */}
      <div className="flex-1 relative">
        {/* Connection Overlay */}
        {!connected && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-red-900/80 text-red-100 rounded-full text-sm font-medium border border-red-500/30 backdrop-blur-md z-10 animate-pulse">
            {error || "Waiting for hardware stream..."}
          </div>
        )}
        
        <Canvas camera={{ position: [0, 1.5, 5], fov: 45 }}>
          <color attach="background" args={['#020617']} />
          <fog attach="fog" args={['#020617', 5, 15]} />
          
          <ambientLight intensity={0.5} />
          <spotLight position={[5, 5, 5]} angle={0.15} penumbra={1} intensity={1} color="#4F46E5" />
          <pointLight position={[-5, -5, -5]} intensity={0.5} color="#06B6D4" />
          
          {/* Aesthetic background particles */}
          <Sparkles count={100} scale={10} size={2} speed={0.4} color="#38BDF8" opacity={0.2} visible={true} />
          <Stars radius={10} depth={50} count={1000} factor={4} saturation={0} fade speed={1} />

          {/* Model Instance */}
          <MedicalModel data={data} />
          
          {/* Controls & Ground Shadow */}
          <OrbitControls 
            enablePan={false} 
            minPolarAngle={Math.PI / 4} 
            maxPolarAngle={Math.PI / 1.5}
            minDistance={2}
            maxDistance={8}
            target={[0, 1.5, 0]}
          />
          <ContactShadows position={[0, -1, 0]} opacity={0.4} scale={10} blur={2} far={10} />
          <Environment preset="city" />
        </Canvas>

        {/* Floating Telemetry HUD */}
        <div className="absolute top-8 left-8 p-6 bg-slate-900/40 backdrop-blur-xl border border-slate-700/50 rounded-2xl w-80 shadow-2xl pointer-events-none">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent mb-6">
                MedVerse Digital Twin
            </h1>
            
            <div className="space-y-4">
                {/* Diagnostics Group */}
                <div>
                    <h3 className="text-xs font-semibold text-slate-400 tracking-wider uppercase mb-2">Patient Status</h3>
                    <div className="grid grid-cols-2 gap-2">
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                            <div className="text-xs text-slate-400">Heart Rate</div>
                            <div className="text-xl font-mono text-red-400">{data?.vitals?.heart_rate || 0} <span className="text-xs">BPM</span></div>
                        </div>
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                            <div className="text-xs text-slate-400">Core Temp</div>
                            <div className="text-xl font-mono text-orange-400">
                                {data?.temperature?.cervical ? data.temperature.cervical.toFixed(1) : "0.0"} <span className="text-xs">°C</span>
                            </div>
                        </div>
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                            <div className="text-xs text-slate-400">Spinal Pitch</div>
                            <div className="text-xl font-mono text-blue-400">
                                {data?.imu?.upper_roll ? data.imu.upper_roll.toFixed(1) : "0.0"} <span className="text-xs">°</span>
                            </div>
                        </div>
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                            <div className="text-xs text-slate-400">Spinal Roll</div>
                            <div className="text-xl font-mono text-blue-400">
                                {data?.imu?.spinal_angle ? data.imu.spinal_angle.toFixed(1) : "0.0"} <span className="text-xs">°</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Obstetrics Group */}
                <div>
                    <h3 className="text-xs font-semibold text-slate-400 tracking-wider uppercase mb-2 mt-4">Fetal Subsystem</h3>
                    <div className="grid grid-cols-1 gap-2">
                        <div className={`p-3 rounded-lg border transition-colors duration-500 flex justify-between items-center ${data?.fetal?.kicks?.some(k => k) ? 'bg-amber-900/40 border-amber-500/50' : 'bg-slate-800/50 border-slate-700/50'}`}>
                            <div className="text-sm font-medium text-slate-200">Fetal Kicks</div>
                            <div className={`text-xs font-mono px-2 py-1 rounded ${data?.fetal?.kicks?.some(k => k) ? 'bg-amber-500/20 text-amber-300' : 'text-slate-500'}`}>
                                {data?.fetal?.kicks?.some(k => k) ? 'DETECTED' : 'QUIET'}
                            </div>
                        </div>
                        <div className={`p-3 rounded-lg border transition-colors duration-500 flex justify-between items-center ${data?.fetal?.contractions?.some(c => c) ? 'bg-red-900/40 border-red-500/50' : 'bg-slate-800/50 border-slate-700/50'}`}>
                            <div className="text-sm font-medium text-slate-200">Contractions</div>
                            <div className={`text-xs font-mono px-2 py-1 rounded ${data?.fetal?.contractions?.some(c => c) ? 'bg-red-500/20 text-red-300 animate-pulse' : 'text-slate-500'}`}>
                                {data?.fetal?.contractions?.some(c => c) ? 'ACTIVE' : 'NONE'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {/* PK/PD centerpiece — drives heart-rate / contractions via /api/simulation/medicate */}
        <div className="absolute top-8 right-8 pointer-events-auto">
          <PharmacologyPanel />
        </div>

      </div>
    </div>
  );
}
