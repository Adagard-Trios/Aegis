"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Radio, Zap, Wifi, WifiOff } from "lucide-react";
import { useVestStream } from "../hooks/useVestStream";
import { getStatus, type BackendStatus } from "../lib/api";

export function DashboardHeader() {
  const { connected } = useVestStream();
  const [status, setStatus] = useState<BackendStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await getStatus();
        if (!cancelled) setStatus(s);
      } catch { /* offline */ }
    };
    tick();
    const id = setInterval(tick, 5_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <motion.h1
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          className="font-display text-2xl font-bold text-foreground tracking-tight"
        >
          Patient Dashboard
        </motion.h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Real-time telemetry from MedVerse Clinical Wearable Platform
        </p>
      </div>
      <div className="flex items-center gap-2">
        <div className={`flex items-center gap-2 border rounded px-3 py-2 shadow-card ${
          connected ? "bg-emerald-500/10 border-emerald-500/30" : "bg-rose-500/10 border-rose-500/30"
        }`}>
          {connected ? <Radio className="w-4 h-4 text-emerald-400 animate-data-pulse" /> : <WifiOff className="w-4 h-4 text-rose-400" />}
          <span className={`text-xs font-medium ${connected ? "text-emerald-400" : "text-rose-400"}`}>
            {connected ? "STREAMING" : "OFFLINE"}
          </span>
        </div>
        {status && (
          <div className="flex items-center gap-2 bg-card border border-border rounded px-3 py-2 shadow-card">
            <Wifi className="w-4 h-4 text-muted-foreground" />
            <span className="text-xs font-mono text-foreground">
              {status.packets_received.toLocaleString()} pkts · {status.sample_rate} Hz
            </span>
          </div>
        )}
        <div className="flex items-center gap-2 bg-card border border-border rounded px-3 py-2 shadow-card">
          <Zap className="w-4 h-4 text-vital-green" />
          <span className="text-xs font-medium text-foreground">{status?.using_mock ? "Mock" : "Live"}</span>
        </div>
      </div>
    </div>
  );
}

export function VestStatusCard() {
  const { data } = useVestStream();
  const conn = data?.connection;
  const live = conn?.vest_connected && !conn?.using_mock;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-secondary rounded-md border border-sidebar-border p-5 flex gap-5 items-center overflow-hidden relative"
    >
      <div className="absolute -top-20 -right-20 w-60 h-60 bg-primary/5 rounded-full blur-3xl" />

      <div className="w-24 h-32 rounded overflow-hidden flex-shrink-0 relative bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
        <div className="text-primary text-3xl font-display font-bold">M</div>
      </div>

      <div className="relative z-10">
        <h3 className="font-display font-semibold text-secondary-foreground text-sm mb-1">
          MedVerse Vest v2.4
        </h3>
        <p className="text-xs text-secondary-foreground/60 mb-2 leading-relaxed">
          15-sensor clinical array • ESP32-S3 dual-core • FreeRTOS
        </p>
        <div className="flex items-center gap-2 mb-2">
          <span className={`flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-sm ${
            live ? "bg-emerald-500/15 text-emerald-300" : conn?.using_mock ? "bg-amber-500/15 text-amber-300" : "bg-rose-500/15 text-rose-300"
          }`}>
            {live ? "VEST CONNECTED" : conn?.using_mock ? "MOCK MODE" : "OFFLINE"}
          </span>
          {conn?.fetal_connected && (
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-sm bg-pink-500/15 text-pink-300">
              FETAL +
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {["Cardiology", "Respiratory", "Biomechanics", "Thermal"].map((mod) => (
            <span
              key={mod}
              className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-sm bg-primary/10 text-primary"
            >
              {mod}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
