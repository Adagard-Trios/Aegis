"use client";

import { useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Activity } from "lucide-react";

function ecgGenerator(t: number, scale = 1, offset = 0): number {
  const period = 0.8;
  const phase = (((t + offset) % period) + period) % period;
  const p = phase / period;
  if (p < 0.1) return 0.1 * Math.sin((p * Math.PI) / 0.1) * 0.15 * scale;
  if (p < 0.15) return 0;
  if (p < 0.18) return -0.08 * scale;
  if (p < 0.22) return 0.9 * Math.sin(((p - 0.18) * Math.PI) / 0.04) * scale;
  if (p < 0.26) return -0.15 * scale;
  if (p < 0.35) return 0;
  if (p < 0.45) return Math.sin(((p - 0.35) * Math.PI) / 0.1) * 0.2 * scale;
  return 0;
}

function ppgGenerator(t: number): number {
  const period = 0.85;
  const phase = ((t % period) + period) % period;
  const p = phase / period;
  const systolic = Math.pow(Math.sin(p * Math.PI * 0.8), 2) * (p < 0.5 ? 1 : 0);
  const dicrotic =
    p > 0.45 && p < 0.65 ? Math.sin(((p - 0.45) * Math.PI) / 0.2) * 0.3 : 0;
  return systolic + dicrotic + Math.sin(t * 0.3) * 0.02;
}

interface WaveformConfig {
  label: string;
  generator: (t: number) => number;
  yRange: [number, number];
  color: string;
  value: string;
  unit: string;
  status: string;
}

function CanvasWaveform({
  generator,
  color,
  yRange,
  height = 90,
}: {
  generator: (t: number) => number;
  color: string;
  yRange: [number, number];
  height?: number;
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

    // Grid
    ctx.strokeStyle = "rgba(0, 212, 255, 0.05)";
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 5; i++) {
      const y = (i / 4) * h;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
    for (let i = 0; i < 10; i++) {
      const x = (i / 9) * w;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    // Waveform
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
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

    // Leading dot
    const lastVal = generator(timeRef.current);
    const lastY = h - ((lastVal - yMin) / (yMax - yMin)) * h;
    ctx.beginPath();
    ctx.arc(w - 1, lastY, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    timeRef.current += 0.03;
    animRef.current = requestAnimationFrame(draw);
  }, [generator, color, yRange]);

  useEffect(() => {
    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      width={500}
      height={height}
      className="w-full"
      style={{ height: `${height}px` }}
    />
  );
}

const LEADS: WaveformConfig[] = [
  {
    label: "Lead I",
    generator: (t) => ecgGenerator(t, 0.85, 0),
    yRange: [-0.3, 1.0],
    color: "hsl(160, 84%, 39%)",
    value: "0.82",
    unit: "mV",
    status: "SINUS RHYTHM",
  },
  {
    label: "Lead II",
    generator: (t) => ecgGenerator(t, 1.0, 0.02),
    yRange: [-0.3, 1.0],
    color: "hsl(160, 84%, 45%)",
    value: "0.94",
    unit: "mV",
    status: "SINUS RHYTHM",
  },
  {
    label: "Lead III",
    generator: (t) => ecgGenerator(t, 0.6, 0.04),
    yRange: [-0.3, 1.0],
    color: "hsl(160, 84%, 52%)",
    value: "0.58",
    unit: "mV",
    status: "SINUS RHYTHM",
  },
];

function LeadCard({
  config,
  delay,
}: {
  config: WaveformConfig;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-card border border-border rounded-md p-4 shadow-card"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {config.label}
        </span>
        <div className="flex items-center gap-2">
          <span className="font-display font-bold text-foreground">
            {config.value}
          </span>
          <span className="text-[10px] text-muted-foreground">
            {config.unit}
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold">
            {config.status}
          </span>
        </div>
      </div>
      <div className="rounded-md overflow-hidden bg-secondary/20 p-1">
        <CanvasWaveform
          generator={config.generator}
          color={config.color}
          yRange={config.yRange}
          height={80}
        />
      </div>
    </motion.div>
  );
}

export function LiveECGMonitor() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {LEADS.map((lead, i) => (
          <LeadCard key={lead.label} config={lead} delay={i * 0.08} />
        ))}
      </div>

      {/* Combined view */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="bg-card border border-border rounded-md p-4 shadow-card"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Combined ECG View
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-accent animate-data-pulse" />
            <span className="text-[10px] text-muted-foreground">
              72 BPM • Sinus Rhythm
            </span>
          </div>
        </div>
        <div className="space-y-1">
          {LEADS.map((lead) => (
            <div key={lead.label} className="flex items-center gap-2">
              <span className="text-[9px] text-muted-foreground w-12 text-right uppercase tracking-wider">
                {lead.label}
              </span>
              <div className="flex-1 rounded overflow-hidden bg-secondary/20 p-0.5">
                <CanvasWaveform
                  generator={lead.generator}
                  color={lead.color}
                  yRange={lead.yRange}
                  height={45}
                />
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* PPG Waveform */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-card border border-border rounded-md p-4 shadow-card"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            PPG Waveform
          </span>
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-foreground">98</span>
            <span className="text-[10px] text-muted-foreground">SpO₂ %</span>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold">
              NORMAL
            </span>
          </div>
        </div>
        <div className="rounded-md overflow-hidden bg-secondary/20 p-1">
          <CanvasWaveform
            generator={ppgGenerator}
            color="hsl(0, 84%, 60%)"
            yRange={[-0.1, 1.2]}
            height={80}
          />
        </div>
      </motion.div>
    </div>
  );
}
