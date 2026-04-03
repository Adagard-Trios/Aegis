"use client";

import { useState, useRef } from "react";
import { Upload, FlaskConical, Clock, HeartPulse, Activity } from "lucide-react";
import { useVestStream } from "../hooks/useVestStream";

export function SimulationControls() {
  const { data } = useVestStream();
  const [activeMode, setActiveMode] = useState<string>("Live");
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [medicationStatus, setMedicationStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modes = ["Live", "6h", "12h", "24h", "2w", "4w"];

  const setSimulationMode = async (mode: string) => {
    setActiveMode(mode);
    try {
      await fetch("http://localhost:8000/api/simulation/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
    } catch (e) {
      console.error("Failed to set mode", e);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploadStatus("Processing Lab Report via Gemini...");
    
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/api/upload-lab-results", {
        method: "POST",
        body: formData,
      });

      const parsedData = await response.json();
      if (parsedData.status === "success") {
        setUploadStatus(`Extraction Complete. Patient detected as: ${parsedData.extracted_data.CYP2D6}. Active Pharmacodynamics matrix updated.`);
        setTimeout(() => setUploadStatus(null), 8000);
      }
    } catch (e) {
      console.error("Failed to upload labs", e);
      setUploadStatus("Extraction Failed.");
    }
    
    // clear input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const injectMedication = async (medication: string, dose: number) => {
    try {
      await fetch("http://localhost:8000/api/simulation/medicate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ medication, dose }),
      });
      setMedicationStatus(`Administering ${medication} - See active Pharmacokinetics below.`);
      setTimeout(() => setMedicationStatus(null), 5000);
    } catch (e) {
      console.error("Failed to inject", e);
    }
  };

  return (
    <div className="bg-card border border-border shadow-sm rounded-xl p-6">
      <div className="flex flex-col mb-4">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-primary" />
          <h2 className="font-display text-lg font-semibold text-foreground tracking-tight">
            Simulation & In-Silico Testing
          </h2>
        </div>
        {uploadStatus && <p className="text-secondary-foreground text-xs bg-secondary px-2 py-1 rounded w-fit mt-2 animate-pulse">{uploadStatus}</p>}
        {medicationStatus && <p className="text-primary-foreground text-xs bg-primary px-2 py-1 rounded w-fit mt-2 animate-pulse">{medicationStatus}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Time Warp Scrubber */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Clock className="w-4 h-4" />
            Time Warp Protocol
          </div>
          <div className="flex flex-wrap gap-2">
            {modes.map((mode) => (
              <button
                key={mode}
                onClick={() => setSimulationMode(mode)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeMode === mode
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        {/* Lab Upload */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Upload className="w-4 h-4" />
            Patient Context Integration
          </div>
          <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept="image/png, image/jpeg, application/pdf" />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-background border border-primary text-primary hover:bg-primary/10 rounded-lg transition-colors font-medium text-sm"
          >
            <Upload className="w-4 h-4" />
            Upload Lab Report (OCR)
          </button>
        </div>

        {/* Medication Engine */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <HeartPulse className="w-4 h-4" />
            Pharmacological Triggers
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => injectMedication("Labetalol", 100)}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium text-sm"
            >
              <Activity className="w-4 h-4" />
              Labetalol 100mg
            </button>
            <button
              onClick={() => injectMedication("Oxytocin", 10)}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors font-medium text-sm"
            >
              <Activity className="w-4 h-4" />
              Oxytocin 10U
            </button>
          </div>
        </div>

      </div>
      
      {data?.pharmacology && data.pharmacology.active_medication && (
        <div className="mt-6 p-4 rounded-lg bg-black/5 border border-primary/20">
          <div className="flex items-center gap-2 mb-2">
            <HeartPulse className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-primary">ACTIVE PHARMACODYNAMICS</h3>
          </div>
          <p className="font-semibold text-lg text-foreground tracking-tight">Medication: {data.pharmacology.active_medication}</p>
          <p className="text-warning text-sm font-medium mt-1">Clearance Profile: {data.pharmacology.clearance_model}</p>
          <p className="text-muted-foreground text-xs mt-1">Simulated Time Elapsed: {data.pharmacology.sim_time.toFixed(1)}s (Accelerated)</p>
          
          <div className="mt-3 bg-black/80 rounded p-3 text-white/80 text-xs italic">
            {data.pharmacology.active_medication.toLowerCase() === 'labetalol' 
              ? `Effect: Maternal Heart Rate forcefully suppressed across exponential decay curve (Scaled by ${data.pharmacology.clearance_model === "Poor Metabolizer" ? "0.1k" : "0.2k"}).`
              : `Effect: Strong oxytocic action stimulating immediate uterine contractions and elevating maternal heart rate.`}
          </div>
        </div>
      )}
    </div>
  );
}
