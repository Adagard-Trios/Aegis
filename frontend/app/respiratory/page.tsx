"use client";

import { useRef, useEffect, useCallback } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Wind, Volume2, Waves, Activity, AlertCircle, TrendingUp, Gauge } from "lucide-react";

function CanvasWave({
  generator,
  color,
  yRange,
}: {
  generator: (t: number) => number;
  color: string;
  yRange: [number, number];
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const timeRef = useRef(0);
  const animRef = useRef<number>(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    const [yMin, yMax] = yRange;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = "rgba(0,212,255,0.05)";
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 5; i++) {
      const y = (i / 4) * h;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.lineJoin = "round";
    for (let i = 0; i < w; i++) {
      const t = timeRef.current - (w - i) * 0.008;
      const val = generator(t);
      const y = h - ((val - yMin) / (yMax - yMin)) * h;
      if (i === 0) ctx.moveTo(i, y);
      else ctx.lineTo(i, y);
    }
    ctx.stroke();
    ctx.shadowColor = color;
    ctx.shadowBlur = 6;
    ctx.stroke();
    ctx.shadowBlur = 0;
    timeRef.current += 0.03;
    animRef.current = requestAnimationFrame(draw);
  }, [generator, color, yRange]);

  useEffect(() => {
    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [draw]);

  return <canvas ref={canvasRef} width={500} height={80} className="w-full h-20" />;
}

const pneumoGen = (t: number) => Math.sin(t * 1.2) * 0.4 + Math.sin(t * 2.4) * 0.08 + 0.5;
const acousticGen = (t: number) =>
  Math.sin(t * 15) * 0.15 + Math.sin(t * 23) * 0.08 + Math.sin(t * 0.8) * 0.3;

export default function RespiratoryPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">
            Respiratory Module
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            I2S acoustic analysis, pneumographic monitoring & pulmonary diagnostics
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Live Pneumogram */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-card border border-border rounded-md p-4 shadow-card"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Waves className="w-4 h-4 text-primary" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Live Pneumogram
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-data-pulse" />
                <span className="text-[10px] text-muted-foreground">Live</span>
              </div>
            </div>
            <div className="rounded-md overflow-hidden bg-secondary/20 p-1">
              <CanvasWave generator={pneumoGen} color="hsl(191, 100%, 50%)" yRange={[-0.1, 1.1]} />
            </div>
          </motion.div>

          {/* Live Acoustic Stream */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-card border border-border rounded-md p-4 shadow-card"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-accent" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  I2S Acoustic Stream
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-accent animate-data-pulse" />
                <span className="text-[10px] text-muted-foreground">Live</span>
              </div>
            </div>
            <div className="rounded-md overflow-hidden bg-secondary/20 p-1">
              <CanvasWave
                generator={acousticGen}
                color="hsl(160, 84%, 39%)"
                yRange={[-0.6, 0.6]}
              />
            </div>
            <p className="text-[10px] text-muted-foreground mt-2">
              No crackles, wheezing, or rhonchi detected
            </p>
          </motion.div>

          {/* Respiratory Metrics */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-card border border-border rounded-md p-4 shadow-card space-y-4"
          >
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Respiratory Metrics
            </h3>
            {[
              { label: "Respiratory Rate", value: "16", unit: "br/min", icon: Wind },
              { label: "SpO₂", value: "98", unit: "%", icon: Activity },
              { label: "Tidal Volume (est.)", value: "520", unit: "mL", icon: TrendingUp },
              { label: "Peak Flow", value: "6.2", unit: "L/s", icon: Waves },
              { label: "VO₂ Max", value: "42", unit: "mL/kg/min", icon: Gauge },
            ].map((m) => (
              <div key={m.label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <m.icon className="w-4 h-4 text-primary" />
                  <span className="text-sm text-foreground">{m.label}</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="font-display font-bold text-foreground">{m.value}</span>
                  <span className="text-xs text-muted-foreground">{m.unit}</span>
                </div>
              </div>
            ))}
          </motion.div>

          {/* Pulmonology Agent Summary */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-card border border-border rounded-md p-4 shadow-card"
          >
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="w-4 h-4 text-accent" />
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Pulmonology Agent Summary
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
                ALL CLEAR
              </span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The Pulmonology AI Agent confirms eupneic breathing pattern with a
              respiratory rate of 16 breaths/min. Deep learning respiratory
              classifier reports clear lung fields bilaterally. No pneumonia
              crackles, asthmatic wheezing, or COPD signatures in the I2S
              acoustic spectrum. SpO₂ remains stable at 98%.
            </p>
          </motion.div>
        </div>

        {/* Advanced Respiratory Diagnostics */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Wind className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Advanced Respiratory Diagnostics
            </h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "COPD Screening", value: "Negative", status: "Normal" },
              { label: "Sleep Apnea Risk", value: "Low", status: "AHI < 5" },
              { label: "Hypoxia Detection", value: "None", status: "SpO₂ > 95%" },
              { label: "Hyperventilation", value: "Not Detected", status: "Normal EtCO₂" },
              { label: "O₂ Saturation Trend", value: "98% ± 1%", status: "Stable" },
              { label: "VO₂ Recovery", value: "< 3 min", status: "Good" },
              { label: "Polysomnography", value: "N/A", status: "Awake" },
              { label: "Respiratory Reserve", value: "Normal", status: "Adequate" },
            ].map((d) => (
              <div key={d.label} className="bg-muted/50 rounded px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  {d.label}
                </p>
                <p className="text-xs font-semibold text-foreground">{d.value}</p>
                <p className="text-[9px] text-accent font-semibold uppercase mt-0.5">
                  {d.status}
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
