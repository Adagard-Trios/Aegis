"use client";

import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Stethoscope, AlertCircle, CheckCircle2, BarChart3 } from "lucide-react";

export default function DiagnosticsPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">
            Diagnostics Console
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Multi-agent cross-evaluation, ML confidence scores & diagnostic summary
          </p>
        </motion.div>

        {/* Overall Status */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-md p-5 shadow-card"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-accent" />
            </div>
            <div>
              <h3 className="font-display text-lg font-bold text-foreground">
                All Systems Nominal
              </h3>
              <p className="text-sm text-muted-foreground">
                No anomalies detected across all 15 sensor channels
              </p>
            </div>
          </div>
        </motion.div>

        {/* Agent Confidence Scores */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Agent Confidence Scores
            </h3>
          </div>
          <div className="space-y-3">
            {[
              { agent: "Cardiology", confidence: 98, color: "bg-destructive" },
              { agent: "Pulmonology", confidence: 97, color: "bg-primary" },
              { agent: "Neurology / Biomechanics", confidence: 95, color: "bg-accent" },
              { agent: "OB/GYN", confidence: 96, color: "bg-pink-500" },
              { agent: "Occlometry / Vascular", confidence: 94, color: "bg-warning" },
              { agent: "General Physician", confidence: 99, color: "bg-violet-500" },
            ].map((a, i) => (
              <motion.div
                key={a.agent}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.05 }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-foreground">{a.agent}</span>
                  <span className="text-xs font-bold text-foreground font-display">
                    {a.confidence}%
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${a.confidence}%` }}
                    transition={{ duration: 0.8, delay: 0.2 + i * 0.1 }}
                    className={`h-full rounded-full ${a.color}`}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Diagnostic Checks */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Stethoscope className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Comprehensive Diagnostic Checks
            </h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Arrhythmia Detection", status: "Clear", icon: "✓" },
              { label: "ST-Segment Analysis", status: "Normal", icon: "✓" },
              { label: "Lung Auscultation", status: "Clear", icon: "✓" },
              { label: "Posture Assessment", status: "Optimal", icon: "✓" },
              { label: "Blood Pressure", status: "Normotensive", icon: "✓" },
              { label: "Temperature", status: "Afebrile", icon: "✓" },
              { label: "Oxygen Saturation", status: "Normal", icon: "✓" },
              { label: "Sepsis Screening", status: "Negative", icon: "✓" },
            ].map((d) => (
              <div key={d.label} className="bg-muted/50 rounded px-3 py-2 flex items-center gap-2">
                <span className="text-accent text-sm">{d.icon}</span>
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                    {d.label}
                  </p>
                  <p className="text-xs font-semibold text-accent">{d.status}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Cross-Agent Alerts */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Cross-Agent Alert Feed
            </h3>
          </div>
          <div className="text-center py-8">
            <CheckCircle2 className="w-8 h-8 text-accent mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              No active alerts. All agents report nominal status.
            </p>
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
