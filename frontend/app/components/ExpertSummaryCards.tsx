"use client";

import { motion } from "framer-motion";
import { Heart, Wind, Baby, Eye, Stethoscope, Brain } from "lucide-react";

interface ExpertSummary {
  expert: string;
  icon: React.ElementType;
  color: string;
  status: "normal" | "attention" | "critical";
  summary: string;
  metrics: { label: string; value: string }[];
}

const EXPERT_SUMMARIES: ExpertSummary[] = [
  {
    expert: "Cardiology",
    icon: Heart,
    color: "hsl(0, 84%, 60%)",
    status: "normal",
    summary:
      "Sinus rhythm confirmed across all leads. No ST-segment elevation or arrhythmia detected. HRV within normal range.",
    metrics: [
      { label: "HR", value: "72 BPM" },
      { label: "QRS", value: "0.08s" },
      { label: "HRV", value: "42ms" },
    ],
  },
  {
    expert: "Pulmonology",
    icon: Wind,
    color: "hsl(191, 100%, 50%)",
    status: "normal",
    summary:
      "Clear lung fields bilaterally. No crackles, wheezing, or rhonchi in acoustic spectrum. Respiratory rate eupneic.",
    metrics: [
      { label: "RR", value: "16 br/min" },
      { label: "SpO₂", value: "98%" },
      { label: "Tidal Vol", value: "520mL" },
    ],
  },
  {
    expert: "Gynecology / Obstetrics",
    icon: Baby,
    color: "hsl(330, 80%, 60%)",
    status: "normal",
    summary:
      "Foetal heart rate baseline 140 BPM with normal variability. No decelerations detected. Reassuring CTG pattern.",
    metrics: [
      { label: "FHR", value: "140 BPM" },
      { label: "Variability", value: "Normal" },
      { label: "Accels", value: "Present" },
    ],
  },
  {
    expert: "Occlometry / Vascular",
    icon: Eye,
    color: "hsl(38, 92%, 50%)",
    status: "normal",
    summary:
      "Peripheral pulse oximetry normal. PPG waveform shows good perfusion index. No vascular occlusion indicators.",
    metrics: [
      { label: "PI", value: "4.2%" },
      { label: "PPG Amp", value: "Normal" },
      { label: "Perfusion", value: "Good" },
    ],
  },
  {
    expert: "Neurology / Biomechanics",
    icon: Brain,
    color: "hsl(160, 84%, 39%)",
    status: "normal",
    summary:
      "Posture score optimal. No tremor frequencies detected. Dual-IMU confirms stable resting upright position.",
    metrics: [
      { label: "Posture", value: "94/100" },
      { label: "Tremor", value: "None" },
      { label: "Gait Sym", value: "97.3%" },
    ],
  },
  {
    expert: "General Physician",
    icon: Stethoscope,
    color: "hsl(260, 60%, 55%)",
    status: "normal",
    summary:
      "All subsystems nominal. Patient vitals within healthy parameters. Core temp 37.1°C. No anomalies flagged by any specialist agent.",
    metrics: [
      { label: "Temp", value: "37.1°C" },
      { label: "Status", value: "All Clear" },
      { label: "Alerts", value: "0" },
    ],
  },
];

const statusColors: Record<string, string> = {
  normal: "bg-accent/10 text-accent",
  attention: "bg-warning/10 text-warning",
  critical: "bg-destructive/10 text-destructive",
};

export function ExpertSummaryCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      {EXPERT_SUMMARIES.map((es, i) => (
        <motion.div
          key={es.expert}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06, duration: 0.35 }}
          className="bg-card border border-border rounded-lg p-4 shadow-card hover:shadow-card-hover transition-all duration-300"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div
                className="w-8 h-8 rounded-md flex items-center justify-center"
                style={{ backgroundColor: `${es.color}15` }}
              >
                <es.icon className="w-4 h-4" style={{ color: es.color }} />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-foreground font-display">
                  {es.expert}
                </h4>
                <span className="text-[10px] text-muted-foreground">
                  AI Agent
                </span>
              </div>
            </div>
            <span
              className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-sm ${
                statusColors[es.status]
              }`}
            >
              {es.status}
            </span>
          </div>

          <p className="text-xs text-muted-foreground leading-relaxed mb-3">
            {es.summary}
          </p>

          <div className="flex gap-3 border-t border-border pt-2">
            {es.metrics.map((m) => (
              <div key={m.label} className="flex-1 text-center">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {m.label}
                </p>
                <p className="text-xs font-bold font-display text-foreground">
                  {m.value}
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
