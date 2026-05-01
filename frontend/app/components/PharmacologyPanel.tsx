"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Activity, Beaker, Dna, Syringe, Wind } from "lucide-react";
import { apiPost } from "../lib/api";
import { useVestStream } from "../hooks/useVestStream";

type Drug = "labetalol" | "oxytocin";
type CYP2D6 = "Normal Metabolizer" | "Poor Metabolizer";

interface CurveSample {
  t: number;
  effect: number;
  hr: number;
  contractions: number;
}

const HISTORY_SECONDS = 60;
const HISTORY_POINTS = HISTORY_SECONDS * 10; // /stream emits at 10 Hz

const DRUGS: Record<Drug, { label: string; tagline: string; vital: string; accent: string }> = {
  labetalol: {
    label: "Labetalol",
    tagline: "α/β-blocker — antihypertensive",
    vital: "ΔHR",
    accent: "from-rose-400 to-amber-400",
  },
  oxytocin: {
    label: "Oxytocin",
    tagline: "Uterotonic — induces contractions",
    vital: "Contractions",
    accent: "from-sky-400 to-violet-400",
  },
};

export function PharmacologyPanel() {
  const { data } = useVestStream();
  const [drug, setDrug] = useState<Drug>("labetalol");
  const [dose, setDose] = useState<number>(50);
  const [cyp, setCyp] = useState<CYP2D6>("Normal Metabolizer");
  const [busy, setBusy] = useState<"inject" | "cyp" | null>(null);
  const [hint, setHint] = useState<string | null>(null);

  const baselineHrRef = useRef<number | null>(null);
  const seriesRef = useRef<CurveSample[]>([]);
  const [series, setSeries] = useState<CurveSample[]>([]);

  // Capture a stable baseline HR before any drug effect kicks in.
  useEffect(() => {
    if (!data?.vitals) return;
    if (baselineHrRef.current === null && !data.pharmacology?.active_medication) {
      baselineHrRef.current = data.vitals.heart_rate;
    }
  }, [data]);

  // Append a sample for every stream tick.
  useEffect(() => {
    if (!data) return;
    const sample: CurveSample = {
      t: data.pharmacology?.sim_time ?? 0,
      effect: data.pharmacology?.effect_curve ?? 0,
      hr: data.vitals?.heart_rate ?? 0,
      contractions:
        (data.fetal?.contractions || []).filter(Boolean).length || 0,
    };
    const next = [...seriesRef.current, sample];
    if (next.length > HISTORY_POINTS) next.splice(0, next.length - HISTORY_POINTS);
    seriesRef.current = next;
    setSeries(next);
  }, [data]);

  const inject = async () => {
    setBusy("inject");
    setHint(null);
    try {
      await apiPost("/api/simulation/medicate", { medication: drug, dose });
      // Fresh injection — reset baseline so ΔHR reads relative to "now".
      baselineHrRef.current = data?.vitals?.heart_rate ?? null;
      seriesRef.current = [];
      setSeries([]);
      setHint(`Injected ${dose} mg ${DRUGS[drug].label}.`);
    } catch (e) {
      setHint(e instanceof Error ? e.message : "inject failed");
    } finally {
      setBusy(null);
    }
  };

  const setMetabolizer = async (next: CYP2D6) => {
    setCyp(next);
    setBusy("cyp");
    setHint(null);
    try {
      await apiPost("/api/simulation/cyp2d6", { status: next });
      setHint(
        next === "Poor Metabolizer"
          ? "CYP2D6 Poor — k_el dropped 40% (drug accumulates)."
          : "CYP2D6 Normal — clearance restored."
      );
    } catch (e) {
      setHint(e instanceof Error ? e.message : "cyp2d6 update failed");
    } finally {
      setBusy(null);
    }
  };

  const live = data?.pharmacology;
  const activeDrug = (live?.active_medication || "").toLowerCase();
  const isLive = !!activeDrug;
  const effectPct = Math.round(((live?.effect_curve ?? 0) * 100));
  const kEl = live?.k_el;

  const hrDelta = useMemo(() => {
    if (baselineHrRef.current === null || !data?.vitals) return 0;
    return Math.round(data.vitals.heart_rate - baselineHrRef.current);
  }, [data]);

  const contractionCount = useMemo(() => {
    return (data?.fetal?.contractions || []).filter(Boolean).length;
  }, [data]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative w-full max-w-md p-5 rounded-2xl bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 shadow-2xl text-slate-100"
    >
      <div
        className={`absolute inset-x-0 -top-px h-px bg-gradient-to-r ${DRUGS[drug].accent}`}
      />

      <header className="flex items-center gap-2 mb-4">
        <Beaker className="w-5 h-5 text-violet-300" />
        <h2 className="text-base font-bold tracking-wide">PK/PD Simulator</h2>
        <span className="ml-auto text-[10px] uppercase tracking-wider text-slate-400">
          two-compartment Bateman
        </span>
      </header>

      {/* Drug picker */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        {(Object.keys(DRUGS) as Drug[]).map((d) => {
          const active = drug === d;
          return (
            <button
              key={d}
              onClick={() => setDrug(d)}
              className={`text-left p-3 rounded-lg border transition-colors ${
                active
                  ? "bg-slate-800 border-violet-400/60"
                  : "bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/70"
              }`}
            >
              <div className="text-sm font-semibold">{DRUGS[d].label}</div>
              <div className="text-[10px] text-slate-400 leading-snug">
                {DRUGS[d].tagline}
              </div>
            </button>
          );
        })}
      </div>

      {/* Dose slider */}
      <label className="block mb-4">
        <div className="flex justify-between text-xs text-slate-300 mb-1">
          <span className="uppercase tracking-wider">Dose</span>
          <span className="font-mono">{dose} mg</span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={dose}
          onChange={(e) => setDose(Number(e.target.value))}
          className="w-full accent-violet-400"
        />
      </label>

      {/* CYP2D6 toggle */}
      <div className="mb-4">
        <div className="flex items-center gap-1.5 text-xs text-slate-300 uppercase tracking-wider mb-1">
          <Dna className="w-3.5 h-3.5" /> CYP2D6 status
        </div>
        <div className="grid grid-cols-2 gap-2">
          {(["Normal Metabolizer", "Poor Metabolizer"] as CYP2D6[]).map((s) => (
            <button
              key={s}
              disabled={busy === "cyp"}
              onClick={() => setMetabolizer(s)}
              className={`text-xs py-1.5 rounded-md border transition-colors ${
                cyp === s
                  ? "bg-violet-500/20 border-violet-400/60 text-violet-100"
                  : "bg-slate-800/40 border-slate-700/50 text-slate-300 hover:bg-slate-800/70"
              }`}
            >
              {s.split(" ")[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Inject */}
      <button
        onClick={inject}
        disabled={busy === "inject" || dose === 0}
        className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-semibold text-sm transition-colors ${
          busy === "inject"
            ? "bg-slate-700 text-slate-300 cursor-not-allowed"
            : "bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-400 hover:to-fuchsia-400 text-white"
        }`}
      >
        <Syringe className="w-4 h-4" />
        {busy === "inject" ? "Injecting..." : `Inject ${DRUGS[drug].label}`}
      </button>

      {hint && (
        <div className="mt-2 text-[11px] text-slate-300/90 italic">{hint}</div>
      )}

      {/* Live readout */}
      <div className="mt-5 grid grid-cols-3 gap-2">
        <Stat
          label="Effect"
          value={`${effectPct}%`}
          sub={isLive ? "active" : "idle"}
          tone={isLive ? "violet" : "muted"}
          icon={Activity}
        />
        <Stat
          label="k_el"
          value={kEl !== undefined ? kEl.toFixed(3) : "—"}
          sub={cyp === "Poor Metabolizer" ? "slowed" : "nominal"}
          tone={cyp === "Poor Metabolizer" ? "amber" : "muted"}
          icon={Wind}
        />
        <Stat
          label={DRUGS[drug].vital}
          value={
            drug === "labetalol"
              ? `${hrDelta > 0 ? "+" : ""}${hrDelta} bpm`
              : `${contractionCount}/2`
          }
          sub={
            drug === "labetalol"
              ? `HR ${data?.vitals?.heart_rate?.toFixed(0) ?? "--"}`
              : contractionCount > 0
                ? "active"
                : "quiet"
          }
          tone={
            drug === "labetalol"
              ? hrDelta < -2
                ? "rose"
                : "muted"
              : contractionCount > 0
                ? "rose"
                : "muted"
          }
          icon={drug === "labetalol" ? Activity : Wind}
        />
      </div>

      {/* Effect-curve chart */}
      <div className="mt-4 h-32 -mx-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <XAxis dataKey="t" hide domain={["auto", "auto"]} />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: "#94a3b8", fontSize: 9 }}
              width={20}
            />
            <Tooltip
              contentStyle={{
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 6,
                fontSize: 11,
              }}
              labelFormatter={(t: number) => `t = ${t.toFixed(1)}s`}
              formatter={(v: number) => v.toFixed(3)}
            />
            <ReferenceLine y={0} stroke="#475569" strokeDasharray="2 2" />
            <Line
              type="monotone"
              dataKey="effect"
              stroke="#a78bfa"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <footer className="mt-2 text-[10px] text-slate-500 leading-snug">
        Bateman: C(t) ∝ (k<sub>abs</sub>/(k<sub>abs</sub>−k<sub>el</sub>))(e<sup>−k<sub>el</sub>t</sup> − e<sup>−k<sub>abs</sub>t</sup>).
        Poor metabolizers retain 60% of normal k<sub>el</sub>, extending effect tail.
      </footer>
    </motion.div>
  );
}

function Stat({
  label,
  value,
  sub,
  tone,
  icon: Icon,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "violet" | "rose" | "amber" | "muted";
  icon: React.ComponentType<{ className?: string }>;
}) {
  const palette = {
    violet: "text-violet-300 border-violet-400/40",
    rose: "text-rose-300 border-rose-400/40",
    amber: "text-amber-300 border-amber-400/40",
    muted: "text-slate-300 border-slate-700/50",
  }[tone];
  return (
    <div className={`p-2 rounded-md bg-slate-800/40 border ${palette}`}>
      <div className="flex items-center gap-1 text-[9px] uppercase tracking-wider opacity-80">
        <Icon className="w-3 h-3" /> {label}
      </div>
      <div className="text-lg font-mono leading-tight">{value}</div>
      <div className="text-[10px] opacity-70">{sub}</div>
    </div>
  );
}

