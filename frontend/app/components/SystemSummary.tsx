"use client";

import { motion } from "framer-motion";
import { Activity, Shield, CheckCircle2 } from "lucide-react";

export function SystemSummary() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="bg-card rounded-md border border-border p-5 shadow-card"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-semibold text-foreground text-sm tracking-wide">
          General Physician Summary
        </h3>
        <div className="flex items-center gap-1.5 text-vital-green">
          <CheckCircle2 className="w-4 h-4" />
          <span className="text-xs font-semibold uppercase tracking-wider">
            All Clear
          </span>
        </div>
      </div>

      <p className="text-sm text-muted-foreground leading-relaxed mb-4">
        All vitals within normal physiological range. Cardiovascular output is
        stable with sinus rhythm confirmed on Lead I and Lead II vectors.
        Respiratory function is optimal—no anomalous acoustic signatures
        detected by the I2S array. Core temperature steady. Biomechanics Agent
        confirms upright posture with minimal motion artifacts.
      </p>

      <div className="grid grid-cols-3 gap-3">
        <SummaryChip icon={Shield} label="Cardiology" status="Clear" />
        <SummaryChip icon={Activity} label="Respiratory" status="Clear" />
        <SummaryChip icon={Shield} label="Posture" status="Optimal" />
      </div>
    </motion.div>
  );
}

function SummaryChip({
  icon: Icon,
  label,
  status,
}: {
  icon: React.ElementType;
  label: string;
  status: string;
}) {
  return (
    <div className="bg-muted/50 rounded px-3 py-2 flex items-center gap-2">
      <Icon className="w-3.5 h-3.5 text-vital-green" />
      <div>
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
          {label}
        </p>
        <p className="text-xs font-semibold text-vital-green">{status}</p>
      </div>
    </div>
  );
}
