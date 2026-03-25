"use client";

import { motion } from "framer-motion";
import { Radio, Zap } from "lucide-react";

export function DashboardHeader() {
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
          Real-time telemetry from Aegis Clinical Wearable Platform
        </p>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-card border border-border rounded px-3 py-2 shadow-card">
          <Radio className="w-4 h-4 text-primary animate-data-pulse" />
          <span className="text-xs font-medium text-foreground">STREAMING</span>
        </div>
        <div className="flex items-center gap-2 bg-card border border-border rounded px-3 py-2 shadow-card">
          <Zap className="w-4 h-4 text-vital-green" />
          <span className="text-xs font-medium text-foreground">Edge Tier</span>
        </div>
      </div>
    </div>
  );
}

export function VestStatusCard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-secondary rounded-md border border-sidebar-border p-5 flex gap-5 items-center overflow-hidden relative"
    >
      {/* Glow effect */}
      <div className="absolute -top-20 -right-20 w-60 h-60 bg-primary/5 rounded-full blur-3xl" />

      <div className="w-24 h-32 rounded overflow-hidden flex-shrink-0 relative bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
        <div className="text-primary text-3xl font-display font-bold">A</div>
      </div>

      <div className="relative z-10">
        <h3 className="font-display font-semibold text-secondary-foreground text-sm mb-1">
          Aegis Vest v2.4
        </h3>
        <p className="text-xs text-secondary-foreground/60 mb-3 leading-relaxed">
          15-sensor clinical array • ESP32-S3 dual-core • FreeRTOS
        </p>
        <div className="flex flex-wrap gap-2">
          {["Cardiology", "Respiratory", "Biomechanics", "Thermal"].map(
            (mod) => (
              <span
                key={mod}
                className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-sm bg-primary/10 text-primary"
              >
                {mod}
              </span>
            )
          )}
        </div>
      </div>
    </motion.div>
  );
}
