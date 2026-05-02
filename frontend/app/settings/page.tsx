"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Wifi, Shield, Bell, Monitor, Bluetooth, Database, Cpu, Save, RefreshCw } from "lucide-react";
import { API_URL, getStatus, type BackendStatus } from "../lib/api";

interface Threshold { min: number; max: number; unit: string; }
type ThresholdMap = Record<string, Threshold>;

const DEFAULT_THRESHOLDS: ThresholdMap = {
  "Heart rate": { min: 40, max: 120, unit: "bpm" },
  "SpO₂": { min: 90, max: 100, unit: "%" },
  "Temperature": { min: 35.0, max: 38.5, unit: "°C" },
  "Breathing rate": { min: 8, max: 25, unit: "rpm" },
  "Spinal angle": { min: -15, max: 15, unit: "°" },
};

const STORAGE_KEY = "medverse_thresholds";

export default function SettingsPage() {
  const [thresholds, setThresholds] = useState<ThresholdMap>(DEFAULT_THRESHOLDS);
  const [status, setStatus] = useState<BackendStatus | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setThresholds({ ...DEFAULT_THRESHOLDS, ...JSON.parse(raw) });
    } catch { /* noop */ }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const s = await getStatus();
        if (!cancelled) setStatus(s);
      } catch { /* offline */ }
    };
    load();
    const id = setInterval(load, 5_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const updateThreshold = (label: string, key: "min" | "max", value: string) => {
    const num = parseFloat(value);
    setThresholds(prev => ({ ...prev, [label]: { ...prev[label], [key]: isNaN(num) ? prev[label][key] : num } }));
  };

  const save = () => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(thresholds));
    setSaved("Saved.");
    setTimeout(() => setSaved(null), 2000);
  };

  const reset = () => setThresholds(DEFAULT_THRESHOLDS);

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Vest configuration, connectivity & alert thresholds
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <Wifi className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Connection</h3>
            <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-sm font-semibold ${status?.vest_connected ? "bg-emerald-500/10 text-emerald-400" : status?.using_mock ? "bg-amber-500/10 text-amber-400" : "bg-rose-500/10 text-rose-400"}`}>
              {status?.vest_connected ? "VEST CONNECTED" : status?.using_mock ? "MOCK" : "OFFLINE"}
            </span>
          </div>
          <div className="space-y-2">
            {[
              { label: "BLE device", value: status?.vest_device ?? "Aegis_SpO2_Live", icon: Bluetooth },
              { label: "Backend API", value: API_URL, icon: Database },
              { label: "Sample rate", value: status ? `${status.sample_rate} Hz` : "—", icon: Cpu },
              { label: "Buffer size", value: status ? `${status.buffer_size} samples` : "—", icon: Monitor },
              { label: "Packets received", value: status ? status.packets_received.toLocaleString() : "—", icon: RefreshCw },
              { label: "Fetal monitor", value: status?.fetal_connected ? "Connected" : "Not detected", icon: Bluetooth },
            ].map((s) => (
              <div key={s.label} className="flex items-center justify-between py-1.5 border-b border-border/40 last:border-0">
                <div className="flex items-center gap-2">
                  <s.icon className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-sm text-foreground">{s.label}</span>
                </div>
                <span className="text-xs text-muted-foreground font-mono bg-muted px-2 py-1 rounded">{s.value}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Alert thresholds</h3>
            <span className="ml-auto flex gap-2">
              <button onClick={reset} className="text-[10px] px-2 py-1 rounded-md bg-muted text-muted-foreground hover:bg-muted/70">Reset</button>
              <button onClick={save} className="text-[10px] px-2 py-1 rounded-md bg-primary/10 text-primary hover:bg-primary/20 flex items-center gap-1">
                <Save className="w-3 h-3" /> Save
              </button>
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(thresholds).map(([label, t]) => (
              <div key={label} className="bg-muted/30 rounded px-3 py-3">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">{label} ({t.unit})</p>
                <div className="flex items-center gap-2 text-xs">
                  <input type="number" value={t.min} onChange={(e) => updateThreshold(label, "min", e.target.value)} className="w-20 bg-background border border-border rounded px-2 py-1 font-mono" />
                  <span className="text-muted-foreground">—</span>
                  <input type="number" value={t.max} onChange={(e) => updateThreshold(label, "max", e.target.value)} className="w-20 bg-background border border-border rounded px-2 py-1 font-mono" />
                </div>
              </div>
            ))}
          </div>
          {saved && <p className="mt-3 text-xs text-emerald-400">{saved}</p>}
          <p className="mt-2 text-[10px] text-muted-foreground italic">
            Stored in browser localStorage. For server-side care plans see /patients/[id]/care-plan.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">System info</h3>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              ["MCU", "ESP32-S3 dual-core"],
              ["OS", "FreeRTOS"],
              ["Backend", "FastAPI + SSE"],
              ["Frontend", "Next.js 16"],
              ["Sample rate", status ? `${status.sample_rate} Hz` : "—"],
              ["Mock mode", status?.using_mock ? "On" : "Off"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1 text-xs">
                <span className="text-muted-foreground">{k}</span>
                <span className="text-foreground font-medium">{v}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
