"use client";

import DashboardLayout from "../components/DashboardLayout";
import { LiveECGMonitor } from "../components/LiveECGMonitor";
import { motion } from "framer-motion";
import { Heart, Waves, AlertCircle } from "lucide-react";

export default function CardiologyPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="font-display text-2xl font-bold text-foreground">
            Cardiology Module
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time cardiovascular monitoring via 5-pad dual-ECG configuration
          </p>
        </motion.div>

        {/* Cardiac Metrics Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
          {[
            { label: "Heart Rate", value: "72", unit: "BPM", color: "hsl(0, 84%, 60%)" },
            { label: "QRS Duration", value: "0.08", unit: "sec", color: "hsl(191, 100%, 50%)" },
            { label: "PR Interval", value: "0.16", unit: "sec", color: "hsl(160, 84%, 39%)" },
            { label: "HRV (SDNN)", value: "42", unit: "ms", color: "hsl(38, 92%, 50%)" },
            { label: "Cuffless BP", value: "118/76", unit: "mmHg", color: "hsl(330, 80%, 60%)" },
            { label: "Stress Level", value: "Low", unit: "", color: "hsl(160, 84%, 39%)" },
          ].map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-card border border-border rounded-md p-3 shadow-card text-center"
            >
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                {m.label}
              </p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="font-display text-2xl font-bold text-foreground">
                  {m.value}
                </span>
                {m.unit && (
                  <span className="text-xs text-muted-foreground">{m.unit}</span>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Live ECG + PPG */}
        <LiveECGMonitor />

        {/* Vascular & Sepsis Monitoring */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Waves className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Vascular & Sepsis Monitoring
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
              NORMAL
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Vasoconstriction", value: "None", status: "Normal" },
              { label: "Perfusion Index", value: "4.2%", status: "Good" },
              { label: "Sepsis Risk (qSOFA)", value: "0/3", status: "Low Risk" },
              { label: "Pulse Pressure", value: "42 mmHg", status: "Normal" },
            ].map((v) => (
              <div key={v.label} className="bg-muted/50 rounded px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {v.label}
                </p>
                <p className="text-xs font-semibold text-foreground">{v.value}</p>
                <p className="text-[9px] text-accent font-semibold uppercase mt-0.5">
                  {v.status}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Cardiology Expert Summary */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Heart className="w-4 h-4 text-destructive" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Cardiology Agent Summary
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
              ALL CLEAR
            </span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            The Cardiology AI Agent confirms stable sinus rhythm across all
            three leads (I, II, III). No arrhythmia patterns detected via ML
            anomaly detection. ST-segment analysis within normal limits. QT
            interval non-prolonged at 0.38s. HRV SDNN of 42ms indicates good
            autonomic balance. PPG waveform shows excellent perfusion with SpO₂
            at 98%. Cuffless BP estimated at 118/76 mmHg (normotensive). Stress
            level assessed as Low based on HRV spectral analysis.
            Vasoconstriction index normal — no peripheral vascular compromise.
          </p>
        </motion.div>

        {/* ML Anomaly Detection */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              ML Anomaly Detection
            </h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Atrial Fibrillation", status: "Not Detected" },
              { label: "Ventricular Tachycardia", status: "Not Detected" },
              { label: "ST Elevation", status: "Normal" },
              { label: "QT Prolongation", status: "Normal" },
              { label: "Hypertensive Crisis", status: "Not Detected" },
              { label: "Cardiac Tamponade", status: "Not Detected" },
              { label: "Vasoconstriction", status: "Normal" },
              { label: "Sepsis Markers", status: "Negative" },
            ].map((a) => (
              <div key={a.label} className="bg-muted/50 rounded px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {a.label}
                </p>
                <p className="text-xs font-semibold text-accent">{a.status}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
