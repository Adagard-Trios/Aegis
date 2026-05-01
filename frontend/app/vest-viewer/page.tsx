"use client";

import React from "react";
import DashboardLayout from "../components/DashboardLayout";
import { VestModel3D } from "../components/VestModel3D";
import { useVestStream } from "../hooks/useVestStream";
import {
  Activity,
  Bluetooth,
  Cpu,
  Heart,
  Radio,
  Thermometer,
  Wind,
} from "lucide-react";

export default function VestViewerPage() {
  const { data, connected, error } = useVestStream();
  const v = data?.vitals;
  const t = data?.temperature;

  return (
    <DashboardLayout>
      <div className="relative h-full w-full bg-slate-950 text-slate-100 overflow-hidden">
        {/* 3D viewer */}
        <div className="absolute inset-0">
          <VestModel3D />
        </div>

        {/* Connection pill */}
        <div className="absolute top-6 left-1/2 -translate-x-1/2 z-10">
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border backdrop-blur-md ${
              connected
                ? "bg-emerald-900/60 border-emerald-500/40 text-emerald-100"
                : "bg-rose-900/70 border-rose-500/40 text-rose-100 animate-pulse"
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            {connected
              ? data?.connection?.using_mock
                ? "STREAMING (mock telemetry)"
                : "STREAMING (live BLE)"
              : error || "Awaiting telemetry stream..."}
          </div>
        </div>

        {/* Sensor sidebar */}
        <aside className="absolute top-6 right-6 w-72 z-10 space-y-3">
          <header className="px-4 py-3 rounded-xl bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 shadow-2xl">
            <h1 className="text-base font-bold tracking-wide">MedVerse Vest</h1>
            <p className="text-[11px] text-slate-400 mt-0.5">
              ESP32-S3 dual-core • 15-sensor clinical array
            </p>
          </header>

          <div className="rounded-xl bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 shadow-2xl divide-y divide-slate-800">
            <Row
              icon={Heart}
              label="Heart rate"
              value={v?.heart_rate?.toFixed(0) ?? "--"}
              unit="bpm"
              tone="rose"
            />
            <Row
              icon={Activity}
              label="SpO₂"
              value={v?.spo2?.toFixed(0) ?? "--"}
              unit="%"
              tone="sky"
            />
            <Row
              icon={Wind}
              label="Resp rate"
              value={v?.breathing_rate?.toFixed(0) ?? "--"}
              unit="rpm"
              tone="emerald"
            />
            <Row
              icon={Thermometer}
              label="Cervical temp"
              value={t?.cervical?.toFixed(1) ?? "--"}
              unit="°C"
              tone="amber"
            />
            <Row
              icon={Cpu}
              label="HRV (RMSSD)"
              value={v?.hrv_rmssd?.toFixed(0) ?? "--"}
              unit="ms"
              tone="violet"
            />
            <Row
              icon={Bluetooth}
              label="Signal"
              value={v?.signal_quality ?? "—"}
              unit=""
              tone="muted"
            />
          </div>

          {data?.scenario && data.scenario !== "normal" && (
            <div className="rounded-xl bg-amber-900/40 border border-amber-500/40 px-3 py-2 text-xs text-amber-100 backdrop-blur-md">
              <span className="font-semibold uppercase tracking-wider">
                Scenario:
              </span>{" "}
              {data.scenario.replace("_", " ")}
            </div>
          )}
        </aside>

        {/* Caption strip */}
        <footer className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-slate-900/60 backdrop-blur-md border border-slate-700/50 text-[11px] text-slate-300 z-10">
          Live BLE telemetry • 12-lead ECG • Dual PPG • IMU posture • Fetal piezo
        </footer>
      </div>
    </DashboardLayout>
  );
}

function Row({
  icon: Icon,
  label,
  value,
  unit,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  unit: string;
  tone: "rose" | "sky" | "emerald" | "amber" | "violet" | "muted";
}) {
  const colors = {
    rose: "text-rose-300",
    sky: "text-sky-300",
    emerald: "text-emerald-300",
    amber: "text-amber-300",
    violet: "text-violet-300",
    muted: "text-slate-300",
  }[tone];
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <Icon className={`w-4 h-4 ${colors}`} />
      <span className="text-[11px] uppercase tracking-wider text-slate-400 flex-1">
        {label}
      </span>
      <span className={`font-mono text-base ${colors}`}>{value}</span>
      {unit && (
        <span className="text-[10px] text-slate-500 font-mono">{unit}</span>
      )}
    </div>
  );
}
