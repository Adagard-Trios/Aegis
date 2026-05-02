"use client";

import { useRef, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Heart, Wind, Activity, Baby } from "lucide-react";

interface WaveformProps {
  title: string;
  icon: React.ComponentType<{ className?: string; color?: string; size?: number; style?: React.CSSProperties }>;
  color: string;
  generator: (t: number) => number;
  yRange: [number, number];
  unit: string;
  value: string;
  delay?: number;
}

function LiveWaveformCanvas({
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

    // Grid lines
    ctx.strokeStyle = "rgba(0, 212, 255, 0.06)";
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 5; i++) {
      const y = (i / 4) * h;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Waveform
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    const points = w;
    for (let i = 0; i < points; i++) {
      const t = timeRef.current - (points - i) * 0.008;
      const val = generator(t);
      const y = h - ((val - yMin) / (yMax - yMin)) * h;
      if (i === 0) ctx.moveTo(i, y);
      else ctx.lineTo(i, y);
    }
    ctx.stroke();

    // Glow effect
    ctx.shadowColor = color;
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Leading dot
    const lastVal = generator(timeRef.current);
    const lastY = h - ((lastVal - yMin) / (yMax - yMin)) * h;
    ctx.beginPath();
    ctx.arc(points - 1, lastY, 3, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    timeRef.current += 0.03;
    animRef.current = requestAnimationFrame(draw);
  }, [generator, color, yRange]);

  useEffect(() => {
    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [draw]);

  return <canvas ref={canvasRef} width={400} height={80} className="w-full h-20" />;
}

function WaveformCard({
  title,
  icon: Icon,
  color,
  generator,
  yRange,
  unit,
  value,
  delay = 0,
}: WaveformProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="bg-card rounded-lg border border-border p-4 shadow-card hover:shadow-card-hover transition-all duration-300"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center"
            style={{ backgroundColor: `${color}15` }}
          >
            <Icon className="w-3.5 h-3.5" style={{ color }} />
          </div>
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {title}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-display text-lg font-bold text-foreground">
            {value}
          </span>
          <span className="text-xs text-muted-foreground">{unit}</span>
        </div>
      </div>
      <div className="rounded-md overflow-hidden bg-secondary/30 p-1">
        <LiveWaveformCanvas generator={generator} color={color} yRange={yRange} />
      </div>
      <div className="mt-2 flex items-center gap-1.5">
        <div
          className="w-1.5 h-1.5 rounded-full animate-data-pulse"
          style={{ backgroundColor: color }}
        />
        <span className="text-[10px] text-muted-foreground">Live stream</span>
      </div>
    </motion.div>
  );
}

// ECG generator
function ecgGenerator(t: number): number {
  const period = 0.8;
  const phase = ((t % period) + period) % period;
  const p = phase / period;
  if (p < 0.1) return 0.1 * Math.sin((p * Math.PI) / 0.1) * 0.15;
  if (p < 0.15) return 0;
  if (p < 0.18) return -0.08;
  if (p < 0.22) return 0.9 * Math.sin(((p - 0.18) * Math.PI) / 0.04);
  if (p < 0.26) return -0.15;
  if (p < 0.35) return 0;
  if (p < 0.45) return Math.sin(((p - 0.35) * Math.PI) / 0.1) * 0.2;
  return 0;
}

// PPG generator
function ppgGenerator(t: number): number {
  const period = 0.85;
  const phase = ((t % period) + period) % period;
  const p = phase / period;
  const systolic = Math.pow(Math.sin(p * Math.PI * 0.8), 2) * (p < 0.5 ? 1 : 0);
  const dicrotic =
    p > 0.45 && p < 0.65
      ? Math.sin(((p - 0.45) * Math.PI) / 0.2) * 0.3
      : 0;
  return systolic + dicrotic + Math.sin(t * 0.3) * 0.02;
}

// Pneumogram
function pneumogramGenerator(t: number): number {
  return Math.sin(t * 1.2) * 0.4 + Math.sin(t * 2.4) * 0.08 + 0.5;
}

// Foetal heart rate
function foetalGenerator(t: number): number {
  const baseline = 140;
  const variability =
    Math.sin(t * 3) * 5 + Math.sin(t * 7) * 3 + Math.sin(t * 0.5) * 8;
  return baseline + variability;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useVestStream } from "../hooks/useVestStream";

export function LiveWaveforms() {
  const { data } = useVestStream();
  const v = data?.vitals;
  const hasFullWaveform = !!data?.waveform;

  return (
    <div>
      {!hasFullWaveform && (
        <p className="text-[10px] text-muted-foreground italic mb-2">
          Showing synthesised previews. Set <code className="bg-muted px-1 rounded">MEDVERSE_INCLUDE_WAVEFORM=true</code> on the backend to receive raw 800-sample buffers.
        </p>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WaveformCard
          title="ECG Lead II"
          icon={Activity}
          color="hsl(160, 84%, 39%)"
          generator={ecgGenerator}
          yRange={[-0.3, 1.0]}
          unit="bpm"
          value={data?.ecg?.ecg_hr?.toFixed(0) ?? "--"}
          delay={0}
        />
        <WaveformCard
          title="PPG Waveform"
          icon={Heart}
          color="hsl(0, 84%, 60%)"
          generator={ppgGenerator}
          yRange={[-0.1, 1.2]}
          unit={`SpO₂ ${v?.spo2?.toFixed(0) ?? "--"}%`}
          value={v?.heart_rate?.toFixed(0) ?? "--"}
          delay={0.08}
        />
        <WaveformCard
          title="Pneumogram"
          icon={Wind}
          color="hsl(191, 100%, 50%)"
          generator={pneumogramGenerator}
          yRange={[-0.1, 1.1]}
          unit="br/min"
          value={v?.breathing_rate?.toFixed(0) ?? "--"}
          delay={0.16}
        />
        <WaveformCard
          title="Foetal Monitor"
          icon={Baby}
          color="hsl(330, 80%, 60%)"
          generator={foetalGenerator}
          yRange={[115, 165]}
          unit="FHR"
          value={String((data?.fetal as { dawes_redman?: { fhr_baseline?: number } } | undefined)?.dawes_redman?.fhr_baseline ?? "140")}
          delay={0.24}
        />
      </div>
    </div>
  );
}
