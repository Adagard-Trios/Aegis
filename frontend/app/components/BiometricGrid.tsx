"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Heart, Wind, Thermometer, Activity, Waves, TrendingUp } from "lucide-react";
import { TelemetryData } from "../hooks/useVestStream";

interface BiometricCardProps {
  title: string;
  value: string;
  unit: string;
  status: "normal" | "warning" | "critical";
  icon: React.ElementType;
  sparkline?: number[];
  delay?: number;
}

function Sparkline({ data, status }: { data: number[]; status: string }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 120;
  const h = 32;

  const points = data
    .map(
      (v, i) =>
        `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`
    )
    .join(" ");

  const color =
    status === "normal"
      ? "hsl(160, 84%, 39%)"
      : status === "warning"
      ? "hsl(38, 92%, 50%)"
      : "hsl(0, 84%, 60%)";

  return (
    <svg width={w} height={h} className="mt-2">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StatusBadge({
  status,
}: {
  status: "normal" | "warning" | "critical";
}) {
  const config = {
    normal: { label: "Normal", classes: "bg-vital-green/10 text-vital-green" },
    warning: { label: "Elevated", classes: "bg-warning/10 text-warning" },
    critical: {
      label: "Critical",
      classes: "bg-destructive/10 text-destructive",
    },
  };
  const c = config[status];
  return (
    <span
      className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-sm ${c.classes}`}
    >
      {c.label}
    </span>
  );
}

export function BiometricCard({
  title,
  value,
  unit,
  status,
  icon: Icon,
  sparkline,
  delay = 0,
}: BiometricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className="bg-card rounded-md border border-border p-4 shadow-card hover:shadow-card-hover transition-shadow duration-200 group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center">
            <Icon className="w-4 h-4 text-primary" />
          </div>
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {title}
          </span>
        </div>
        <StatusBadge status={status} />
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="font-display text-3xl font-bold text-foreground tracking-tight">
          {value}
        </span>
        <span className="text-sm text-muted-foreground font-medium">
          {unit}
        </span>
      </div>
      {sparkline && <Sparkline data={sparkline} status={status} />}
      <div className="mt-2 w-full h-px bg-border" />
      <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-data-pulse" />
        <span>Live monitoring</span>
      </div>
    </motion.div>
  );
}

function genSparkline(base: number, variance: number, count = 20): number[] {
  return Array.from(
    { length: count },
    () => base + (Math.random() - 0.5) * variance * 2
  );
}

function getHrStatus(hr: number): "normal" | "warning" | "critical" {
  if (hr >= 50 && hr <= 100) return "normal";
  if (hr >= 40 && hr <= 120) return "warning";
  return "critical";
}

function getSpo2Status(spo2: number): "normal" | "warning" | "critical" {
  if (spo2 >= 95) return "normal";
  if (spo2 >= 90) return "warning";
  return "critical";
}

function getTempStatus(t: number): "normal" | "warning" | "critical" {
  if (t >= 36.0 && t <= 37.5) return "normal";
  if (t >= 35.0 && t <= 38.5) return "warning";
  return "critical";
}

export function BiometricGrid({ data }: { data: TelemetryData | null }) {
  const cards = useMemo(() => {
    if (data) {
      return [
        {
          title: "Heart Rate",
          value: data.vitals.heart_rate > 0 ? String(data.vitals.heart_rate) : "72",
          unit: "BPM",
          status: data.vitals.heart_rate > 0 ? getHrStatus(data.vitals.heart_rate) : ("normal" as const),
          icon: Heart,
          sparkline: genSparkline(data.vitals.heart_rate || 72, 8),
        },
        {
          title: "ECG Lead I",
          value: data.ecg.lead1 !== 0 ? String(Math.abs(data.ecg.lead1).toFixed(2)) : "0.84",
          unit: "mV",
          status: "normal" as const,
          icon: Activity,
          sparkline: genSparkline(0.84, 0.3),
        },
        {
          title: "SpO₂",
          value: data.vitals.spo2 > 0 ? String(data.vitals.spo2) : "98",
          unit: "%",
          status: data.vitals.spo2 > 0 ? getSpo2Status(data.vitals.spo2) : ("normal" as const),
          icon: Waves,
          sparkline: genSparkline(data.vitals.spo2 || 98, 1.5),
        },
        {
          title: "Respiratory Rate",
          value: data.vitals.breathing_rate > 0 ? String(data.vitals.breathing_rate) : "16",
          unit: "br/min",
          status: "normal" as const,
          icon: Wind,
          sparkline: genSparkline(data.vitals.breathing_rate || 16, 3),
        },
        {
          title: "Core Temperature",
          value: data.temperature.cervical > 0 ? data.temperature.cervical.toFixed(1) : "36.8",
          unit: "°C",
          status: data.temperature.cervical > 0 ? getTempStatus(data.temperature.cervical) : ("normal" as const),
          icon: Thermometer,
          sparkline: genSparkline(data.temperature.cervical || 36.8, 0.3),
        },
        {
          title: "HRV (RMSSD)",
          value: data.vitals.hrv_rmssd > 0 ? String(data.vitals.hrv_rmssd) : "42",
          unit: "ms",
          status: "normal" as const,
          icon: TrendingUp,
          sparkline: genSparkline(data.vitals.hrv_rmssd || 42, 10),
        },
        {
          title: "Fetal Kicks",
          value: data.fetal?.kicks.some(k => k) ? "Active" : "None",
          unit: "",
          status: data.fetal?.kicks.some(k => k) ? ("normal" as const) : ("warning" as const),
          icon: Activity,
          sparkline: genSparkline(data.fetal?.kicks.some(k => k) ? 1 : 0, 1),
        },
        {
          title: "Uterine Contractions",
          value: data.fetal?.contractions.some(c => c) ? "True" : "False",
          unit: "",
          status: data.fetal?.contractions.some(c => c) ? ("critical" as const) : ("normal" as const),
          icon: Activity,
          sparkline: genSparkline(data.fetal?.contractions.some(c => c) ? 1 : 0, 1),
        },
        {
          title: "Spinal Angle (Posture)",
          value: data.imu.spinal_angle !== undefined ? data.imu.spinal_angle.toFixed(1) : "0.0",
          unit: "°",
          status: data.imu.poor_posture ? ("critical" as const) : ("normal" as const),
          icon: Activity,
          sparkline: genSparkline(data.imu.spinal_angle || 0, 5),
        },
        {
          title: "Environmental Temp",
          value: data.environment?.bmp280_temp ? data.environment.bmp280_temp.toFixed(1) : "22.5",
          unit: "°C",
          status: "normal" as const,
          icon: Thermometer,
          sparkline: genSparkline(data.environment?.bmp280_temp || 22.5, 0.5),
        },
      ];
    }
    return [
      { title: "Heart Rate", value: "72", unit: "BPM", status: "normal" as const, icon: Heart, sparkline: genSparkline(72, 8) },
      { title: "ECG Lead I", value: "0.84", unit: "mV", status: "normal" as const, icon: Activity, sparkline: genSparkline(0.84, 0.3) },
      { title: "SpO₂", value: "98", unit: "%", status: "normal" as const, icon: Waves, sparkline: genSparkline(98, 1.5) },
      { title: "Respiratory Rate", value: "16", unit: "br/min", status: "normal" as const, icon: Wind, sparkline: genSparkline(16, 3) },
      { title: "Core Temperature", value: "36.8", unit: "°C", status: "normal" as const, icon: Thermometer, sparkline: genSparkline(36.8, 0.3) },
      { title: "HRV (RMSSD)", value: "42", unit: "ms", status: "normal" as const, icon: TrendingUp, sparkline: genSparkline(42, 10) },
      { title: "Fetal Kicks", value: "None", unit: "", status: "normal" as const, icon: Activity, sparkline: genSparkline(0, 1) },
      { title: "Uterine Contractions", value: "False", unit: "", status: "normal" as const, icon: Activity, sparkline: genSparkline(0, 1) },
      { title: "Spinal Angle (Posture)", value: "0.0", unit: "°", status: "normal" as const, icon: Activity, sparkline: genSparkline(0, 5) },
      { title: "Environmental Temp", value: "22.5", unit: "°C", status: "normal" as const, icon: Thermometer, sparkline: genSparkline(22.5, 0.5) },
    ];
  }, [data]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {cards.map((card, i) => (
        <BiometricCard key={card.title} {...card} delay={i * 0.05} />
      ))}
    </div>
  );
}
