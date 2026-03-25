"use client";

import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import {
  Brain, Compass, Activity, Move, AlertCircle, RotateCcw,
  Moon, ShieldAlert, Footprints, Heart,
} from "lucide-react";

export default function NeurologyPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">
            Neurology & Biomechanics
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Dual-IMU spatial array, posture calibration, fall detection & cognitive monitoring
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[
            { title: "Posture Score", value: "94", unit: "/100", icon: Compass, status: "Optimal" },
            { title: "Spinal Alignment", value: "2.1", unit: "° deviation", icon: RotateCcw, status: "Normal" },
            { title: "Gait Symmetry", value: "97.3", unit: "%", icon: Move, status: "Symmetric" },
            { title: "Tremor Freq.", value: "0.0", unit: "Hz", icon: Activity, status: "None Detected" },
            { title: "Fall Detection", value: "Clear", unit: "", icon: ShieldAlert, status: "No Falls" },
            { title: "Gait Instability", value: "Low", unit: "risk", icon: Footprints, status: "Stable" },
            { title: "Stress Level", value: "Low", unit: "", icon: Heart, status: "Calm" },
            { title: "Physical State", value: "Resting", unit: "", icon: AlertCircle, status: "Sedentary" },
            { title: "Fall Risk Score", value: "2", unit: "/10", icon: ShieldAlert, status: "Low Risk" },
          ].map((card, i) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              className="bg-card border border-border rounded-md p-4 shadow-card"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center">
                  <card.icon className="w-4 h-4 text-primary" />
                </div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {card.title}
                </span>
              </div>
              <div className="flex items-baseline gap-1.5 mb-2">
                <span className="font-display text-3xl font-bold text-foreground">
                  {card.value}
                </span>
                <span className="text-sm text-muted-foreground">{card.unit}</span>
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-accent">
                {card.status}
              </span>
            </motion.div>
          ))}
        </div>

        {/* Panic, PTSD & Autonomic Monitoring */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Panic, PTSD & Autonomic Monitoring
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
              STABLE
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Panic Episode", value: "None", status: "Clear" },
              { label: "PTSD Trigger", value: "Not Detected", status: "Calm" },
              { label: "Autonomic Hijack", value: "None", status: "Normal SNS/PNS" },
              { label: "HRV LF/HF Ratio", value: "1.2", status: "Balanced" },
            ].map((p) => (
              <div key={p.label} className="bg-muted/50 rounded px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {p.label}
                </p>
                <p className="text-xs font-semibold text-foreground">{p.value}</p>
                <p className="text-[9px] text-accent font-semibold uppercase mt-0.5">
                  {p.status}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Sleep & Polysomnography */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Moon className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Sleep & Polysomnography
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-primary/10 text-primary font-semibold ml-auto">
              AWAKE
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Sleep Position", value: "N/A", status: "Upright" },
              { label: "Polysomnography", value: "Standby", status: "Awake" },
              { label: "Sleep Apnea Risk", value: "Low", status: "AHI < 5" },
              { label: "Sleep Quality", value: "—", status: "Not Sleeping" },
            ].map((s) => (
              <div key={s.label} className="bg-muted/50 rounded px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {s.label}
                </p>
                <p className="text-xs font-semibold text-foreground">{s.value}</p>
                <p className="text-[9px] text-muted-foreground font-semibold uppercase mt-0.5">
                  {s.status}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Neurology Expert Summary */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Neurology & Biomechanics Agent Summary
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
              ALL CLEAR
            </span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            The Biomechanics AI Agent confirms the patient is in a resting
            upright posture with a posture score of 94/100. Dual-IMU data
            shows minimal deviation (2.1°) from calibrated spinal baseline.
            Gait symmetry at 97.3% indicates balanced locomotion. No tremor
            frequencies detected. Fall detection system active — no events
            recorded; fall risk score 2/10 (low). Continuous monitoring active.
          </p>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
