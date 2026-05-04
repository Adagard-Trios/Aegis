"use client";

/**
 * Twin timeline scrubber for /digital-twin.
 *
 * Bottom-of-page bar that lets the clinician scrub through historical
 * twin states. Pulls /api/digital-twin/timeline for the last
 * `windowMinutes` (default 60) and renders:
 *   - A horizontal slider whose tick range maps to the index in `states`
 *   - A "live" pill that shows the most recent state by default
 *   - The currently-selected state's key fields rendered as small KPIs
 *
 * Doesn't drive the 3D model directly (that's wired off `useVestStream`
 * for the live path). When the user scrubs back, we surface the picked
 * state so they can read history; integrating the slider with the 3D
 * twin's `twinState` prop is a follow-up once the existing 3D component
 * accepts external state.
 */
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Clock, History, Heart, Activity, Pause, Play } from "lucide-react";
import { useTwinTimeline } from "../hooks/useTwinTimeline";
import type { TwinName } from "../lib/api";

const WINDOWS = [
  { value: 15,   label: "15 m" },
  { value: 60,   label: "1 h"  },
  { value: 360,  label: "6 h"  },
  { value: 1440, label: "24 h" },
];

const TWINS: { value: TwinName; label: string }[] = [
  { value: "cardiac", label: "Cardiac" },
  { value: "maternal_fetal", label: "Maternal-fetal" },
];

function relativeAgo(epochSec: number): string {
  if (!epochSec) return "—";
  const dtSec = Math.floor(Date.now() / 1000 - epochSec);
  if (dtSec < 60) return `${dtSec}s ago`;
  if (dtSec < 3600) return `${Math.floor(dtSec / 60)}m ago`;
  return `${Math.floor(dtSec / 3600)}h ${Math.floor((dtSec % 3600) / 60)}m ago`;
}

function StateKpi({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <div className="px-2 py-1 rounded border border-white/10 bg-white/5">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`font-mono text-sm ${color}`}>{value}<span className="text-[10px] text-slate-500 ml-1">{unit}</span></div>
    </div>
  );
}

export default function TwinTimelineSlider({ patientId }: { patientId: string | null }) {
  const [twin, setTwin] = useState<TwinName>("cardiac");
  const [windowMinutes, setWindowMinutes] = useState(60);
  const [paused, setPaused] = useState(false);
  const [scrubIdx, setScrubIdx] = useState<number | null>(null);

  const { states, loading } = useTwinTimeline({
    twin,
    patientId,
    windowMinutes,
    refreshSeconds: 10,
    enabled: !paused,
  });

  // When new data arrives and we're not actively scrubbing, snap to the latest entry.
  useEffect(() => {
    if (scrubIdx === null && states.length > 0) {
      // No-op: scrubIdx === null already means "show latest"
    }
  }, [states, scrubIdx]);

  const selected = useMemo(() => {
    if (states.length === 0) return null;
    const idx = scrubIdx ?? states.length - 1;
    return states[Math.min(idx, states.length - 1)];
  }, [states, scrubIdx]);

  const isLive = scrubIdx === null || scrubIdx >= states.length - 1;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="m-4 bg-slate-950/80 backdrop-blur-md border border-slate-700/50 rounded-md p-3 space-y-2"
    >
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-violet-300" />
          <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">Twin timeline</span>
        </div>

        <select
          value={twin}
          onChange={(e) => { setTwin(e.target.value as TwinName); setScrubIdx(null); }}
          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
        >
          {TWINS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>

        <div className="flex gap-1">
          {WINDOWS.map((w) => (
            <button
              key={w.value}
              onClick={() => { setWindowMinutes(w.value); setScrubIdx(null); }}
              className={`px-2 py-1 text-[10px] rounded transition-colors ${
                windowMinutes === w.value
                  ? "bg-violet-500/20 text-violet-200 border border-violet-400/40"
                  : "bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10"
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>

        <button
          onClick={() => setPaused((p) => !p)}
          className="ml-auto flex items-center gap-1 px-2 py-1 rounded text-[10px] bg-white/5 text-slate-300 border border-white/10 hover:bg-white/10"
        >
          {paused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
          {paused ? "Resume" : "Pause"}
        </button>

        {isLive && !paused ? (
          <span className="flex items-center gap-1 text-[10px] text-emerald-300 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> LIVE
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[10px] text-amber-300 font-semibold">
            <Clock className="w-3 h-3" />
            {selected ? relativeAgo(selected.ts) : "—"}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 text-xs">
        <input
          type="range"
          min={0}
          max={Math.max(0, states.length - 1)}
          value={scrubIdx ?? Math.max(0, states.length - 1)}
          onChange={(e) => {
            const v = Number(e.target.value);
            setScrubIdx(v >= states.length - 1 ? null : v);
          }}
          className="flex-1 accent-violet-500"
          disabled={states.length < 2}
        />
        <span className="font-mono text-[10px] text-slate-500 w-24 text-right">
          {states.length > 0
            ? `${(scrubIdx ?? states.length - 1) + 1} / ${states.length}`
            : loading ? "loading…" : "no data"}
        </span>
      </div>

      {selected && (
        <div className="flex flex-wrap gap-2 pt-1">
          {twin === "cardiac" && (
            <>
              <StateKpi label="HR" value={String(selected.state.hr_bpm ?? "—")} unit="bpm" color="text-rose-300" />
              <StateKpi label="HRV" value={String(selected.state.hrv_rmssd ?? "—")} unit="ms" color="text-emerald-300" />
              <StateKpi
                label="Boluses"
                value={String((selected.state.boluses as unknown[] | undefined)?.length ?? 0)}
                unit=""
                color="text-violet-300"
              />
            </>
          )}
          {twin === "maternal_fetal" && (
            <>
              <StateKpi label="FHR" value={String(selected.state.fhr_bpm ?? "—")} unit="bpm" color="text-cyan-300" />
              <StateKpi label="Uterine" value={String(selected.state.uterine_activity ?? "—")} unit="" color="text-orange-300" />
              <StateKpi label="Contr/10m" value={String(selected.state.contractions_per_10min ?? "—")} unit="" color="text-rose-300" />
              <StateKpi label="Cervix" value={String(selected.state.cervix_score ?? "—")} unit="/10" color="text-violet-300" />
            </>
          )}
          <span className="ml-auto flex items-center gap-1 text-[10px] text-slate-500 font-mono">
            <Activity className="w-3 h-3" />
            ts {Math.floor(selected.ts)}
          </span>
        </div>
      )}
    </motion.div>
  );
}
