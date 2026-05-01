"use client";

import React, { useState, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, ContactShadows, Stars, Sparkles } from '@react-three/drei';
import MedicalModel from '../digital-twin/MedicalModel';
import { useVestStream, TelemetryData } from '../hooks/useVestStream';
import { apiPost } from '../lib/api';

type SimulationMode = 'Live' | '6h' | '12h' | '24h' | '2w' | '4w';

export function MedVerseDigitalTwin() {
  const { data, connected, error } = useVestStream();
  const [simulationMode, setSimulationMode] = useState<SimulationMode>('Live');

  const handleSimulationModeChange = async (mode: SimulationMode) => {
    setSimulationMode(mode);
    try {
      await apiPost('/api/simulation/mode', { mode });
    } catch (e) {
      console.error('Failed to sync simulation mode to backend', e);
    }
  };

  const displayData = data;

  return (
    <div className="flex w-full h-full relative font-sans">
      {/* 3D Canvas Context */}
      <div className="flex-1 relative rounded-lg overflow-hidden bg-[#020617] border border-border">
        {/* Connection Overlay */}
        {!connected && simulationMode === 'Live' && (
          <div className="absolute top-4 right-4 px-4 py-2 bg-red-900/80 text-red-100 rounded-full text-sm font-medium border border-red-500/30 backdrop-blur-md z-10 animate-pulse">
            {error || "Waiting for hardware stream..."}
          </div>
        )}

        {/* Prediction Alert Overlay */}
        {simulationMode !== 'Live' && (
          <div className="absolute top-4 right-4 px-4 py-2 bg-indigo-900/80 text-indigo-100 rounded-full text-xs font-bold border border-indigo-500/50 backdrop-blur-md z-10 font-display tracking-widest uppercase">
            In-Silico Prediction: {simulationMode}
          </div>
        )}
        
        {/* Adjusted Camera to Centralize the Model Better */}
        <Canvas camera={{ position: [0, 0.5, 3.5], fov: 45 }}>
          <color attach="background" args={['#020617']} />
          <fog attach="fog" args={['#020617', 5, 15]} />
          
          <ambientLight intensity={0.5} />
          <spotLight position={[5, 5, 5]} angle={0.15} penumbra={1} intensity={1} color="#4F46E5" />
          <pointLight position={[-5, -5, -5]} intensity={0.5} color="#06B6D4" />
          
          <Sparkles count={100} scale={10} size={2} speed={0.4} color="#38BDF8" opacity={0.2} visible={true} />
          <Stars radius={10} depth={50} count={1000} factor={4} saturation={0} fade speed={1} />

          {/* Model Instance accepts simulationMode to trigger physical womb scaling */}
          <MedicalModel data={displayData} simulationMode={simulationMode} />
          
          {/* Target completely centralized on the Torso origin */}
          <OrbitControls 
            enablePan={false} 
            minPolarAngle={Math.PI / 4} 
            maxPolarAngle={Math.PI / 1.5}
            minDistance={2}
            maxDistance={8}
            target={[0, 0.5, 0]}
          />
          <ContactShadows position={[0, -1, 0]} opacity={0.4} scale={10} blur={2} far={10} />
          <Environment preset="city" />
        </Canvas>

        {/* HUD uses displayData (Mocked or Live) */}
        <div className="absolute top-4 left-4 p-4 bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-xl w-64 shadow-2xl pointer-events-none hidden md:block">
            <h2 className="text-base font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent mb-3">
                MedVerse Digital Twin
            </h2>
            
            <div className="space-y-3">
                {/* Diagnostics Group */}
                <div>
                    <h3 className="text-[9px] font-semibold text-slate-400 tracking-wider uppercase mb-1">Patient Status</h3>
                    <div className="grid grid-cols-2 gap-1.5">
                        <div className="bg-slate-800/80 p-2 rounded border border-slate-700/50">
                            <div className="text-[9px] text-slate-400">Heart Rate</div>
                            <div className="text-xs font-mono text-red-400">{displayData?.vitals?.heart_rate || 0} <span className="text-[9px]">BPM</span></div>
                        </div>
                        <div className="bg-slate-800/80 p-2 rounded border border-slate-700/50">
                            <div className="text-[9px] text-slate-400">Core Temp</div>
                            <div className="text-xs font-mono text-orange-400">
                                {displayData?.temperature?.cervical ? displayData.temperature.cervical.toFixed(1) : "0.0"} <span className="text-[9px]">°C</span>
                            </div>
                        </div>
                        <div className="bg-slate-800/80 p-2 rounded border border-slate-700/50">
                            <div className="text-[9px] text-slate-400">Spinal Pitch</div>
                            <div className="text-xs font-mono text-blue-400">
                                {displayData?.imu?.upper_roll ? displayData.imu.upper_roll.toFixed(1) : "0.0"} <span className="text-[9px]">°</span>
                            </div>
                        </div>
                        <div className="bg-slate-800/80 p-2 rounded border border-slate-700/50">
                            <div className="text-[9px] text-slate-400">Spinal Roll</div>
                            <div className="text-xs font-mono text-blue-400">
                                {displayData?.imu?.spinal_angle ? displayData.imu.spinal_angle.toFixed(1) : "0.0"} <span className="text-[9px]">°</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Obstetrics Group */}
                <div>
                    <h3 className="text-[9px] font-semibold text-slate-400 tracking-wider uppercase mb-1 mt-2">Fetal Subsystem</h3>
                    <div className="grid grid-cols-1 gap-1.5">
                        <div className={`p-2 rounded border transition-colors duration-500 flex justify-between items-center ${displayData?.fetal?.kicks?.some(k => k) ? 'bg-amber-900/60 border-amber-500/50' : 'bg-slate-800/80 border-slate-700/50'}`}>
                            <div className="text-[10px] font-medium text-slate-200">Fetal Kicks</div>
                            <div className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${displayData?.fetal?.kicks?.some(k => k) ? 'bg-amber-500/20 text-amber-300' : 'text-slate-500'}`}>
                                {displayData?.fetal?.kicks?.some(k => k) ? 'DETECTED' : 'QUIET'}
                            </div>
                        </div>
                        <div className={`p-2 rounded border transition-colors duration-500 flex justify-between items-center ${displayData?.fetal?.contractions?.some(c => c) ? 'bg-red-900/60 border-red-500/50' : 'bg-slate-800/80 border-slate-700/50'}`}>
                            <div className="text-[10px] font-medium text-slate-200">Contractions</div>
                            <div className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${displayData?.fetal?.contractions?.some(c => c) ? 'bg-red-500/20 text-red-300 animate-pulse' : 'text-slate-500'}`}>
                                {displayData?.fetal?.contractions?.some(c => c) ? 'ACTIVE' : 'NONE'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {/* Temporal Scrubber UI */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 p-1.5 bg-slate-900/90 backdrop-blur-xl border border-slate-600/50 rounded-2xl flex items-center gap-1 shadow-[0_0_30px_rgba(0,0,0,0.5)] z-20 pointer-events-auto">
           {(['Live', '6h', '12h', '24h', '2w', '4w'] as SimulationMode[]).map(mode => (
             <button
               key={mode}
               onClick={() => handleSimulationModeChange(mode)}
               className={`px-3 py-2 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${
                 simulationMode === mode
                 ? 'bg-indigo-600 text-white shadow-[0_0_15px_rgba(79,70,229,0.8)]'
                 : 'text-slate-400 hover:text-white hover:bg-slate-800'
               }`}
             >
               {mode === 'Live' ? 'Live Stream' : `+ ${mode}`}
             </button>
           ))}
        </div>

      </div>
    </div>
  );
}
