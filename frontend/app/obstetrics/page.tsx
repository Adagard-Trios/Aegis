"use client";

import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Baby, Heart, Activity, AlertCircle, Waves, Thermometer } from "lucide-react";

export default function ObstetricsPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">
            Obstetrics & Gynecology
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Foetal monitoring, CTG analysis & maternal health tracking
          </p>
        </motion.div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
          {[
            { label: "Foetal HR", value: "140", unit: "BPM", icon: Baby },
            { label: "Variability", value: "Normal", unit: "", icon: Activity },
            { label: "Accelerations", value: "Present", unit: "", icon: Waves },
            { label: "Decelerations", value: "None", unit: "", icon: AlertCircle },
            { label: "Maternal HR", value: "72", unit: "BPM", icon: Heart },
            { label: "Maternal Temp", value: "36.8", unit: "°C", icon: Thermometer },
          ].map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-card border border-border rounded-md p-3 shadow-card text-center"
            >
              <m.icon className="w-4 h-4 text-primary mx-auto mb-1" />
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                {m.label}
              </p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="font-display text-xl font-bold text-foreground">{m.value}</span>
                {m.unit && <span className="text-xs text-muted-foreground">{m.unit}</span>}
              </div>
            </motion.div>
          ))}
        </div>

        {/* CTG Assessment */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Baby className="w-4 h-4 text-pink-500" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              CTG Assessment
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
              REASSURING
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Baseline FHR", value: "140 BPM", status: "Normal (110-160)" },
              { label: "Beat-to-Beat", value: "8 BPM", status: "Normal (5-25)" },
              { label: "Accelerations", value: "2 in 20min", status: "Reactive" },
              { label: "Decelerations", value: "None", status: "Reassuring" },
              { label: "Uterine Activity", value: "None", status: "No Contractions" },
              { label: "CTG Classification", value: "Category I", status: "Normal" },
              { label: "Dawes-Redman", value: "Pass", status: "Criteria Met" },
              { label: "STV", value: "7.2 ms", status: "Normal (>3.0)" },
            ].map((d) => (
              <div key={d.label} className="bg-muted/50 rounded px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{d.label}</p>
                <p className="text-xs font-semibold text-foreground">{d.value}</p>
                <p className="text-[9px] text-accent font-semibold uppercase mt-0.5">{d.status}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* OB/GYN Agent Summary */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Baby className="w-4 h-4 text-pink-500" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              OB/GYN Agent Summary
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
              ALL CLEAR
            </span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Foetal heart rate baseline at 140 BPM with normal beat-to-beat variability.
            Reassuring CTG pattern — Category I classification. Two accelerations
            detected in the last 20 minutes, confirming reactive status. No decelerations
            observed. Dawes-Redman criteria met. Short-term variability (STV) at 7.2ms
            (normal range). Maternal vitals stable. Continuous monitoring active.
          </p>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
