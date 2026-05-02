"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, Heart, Baby, Wind, ZapOff } from "lucide-react";
import { getScenario, setScenario as postScenario, type Scenario } from "../lib/api";

const SCENARIOS: { id: Scenario; label: string; icon: typeof Activity; tone: string; description: string }[] = [
  { id: "normal", label: "Normal", icon: Activity, tone: "emerald", description: "Pass-through baseline" },
  { id: "tachycardia", label: "Tachycardia", icon: Heart, tone: "rose", description: "HR ~138 bpm" },
  { id: "hypoxia", label: "Hypoxia", icon: Wind, tone: "amber", description: "SpO₂ ~88%" },
  { id: "fetal_decel", label: "Fetal decel", icon: Baby, tone: "rose", description: "Late decelerations" },
  { id: "arrhythmia", label: "Arrhythmia", icon: ZapOff, tone: "amber", description: "HRV spike + transients" },
];

const TONE: Record<string, string> = {
  emerald: "border-emerald-400/40 hover:bg-emerald-500/10 data-[active=true]:bg-emerald-500/20 data-[active=true]:text-emerald-200",
  rose: "border-rose-400/40 hover:bg-rose-500/10 data-[active=true]:bg-rose-500/20 data-[active=true]:text-rose-200",
  amber: "border-amber-400/40 hover:bg-amber-500/10 data-[active=true]:bg-amber-500/20 data-[active=true]:text-amber-200",
};

export function ScenarioPicker() {
  const [active, setActive] = useState<Scenario>("normal");
  const [busy, setBusy] = useState<Scenario | null>(null);

  useEffect(() => {
    let cancelled = false;
    getScenario()
      .then((r) => !cancelled && setActive(r.scenario))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const choose = async (s: Scenario) => {
    setBusy(s);
    try {
      await postScenario(s);
      setActive(s);
    } catch (e) {
      console.error("scenario set failed", e);
    } finally {
      setBusy(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-2xl bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 shadow-2xl text-slate-100 w-full max-w-md"
    >
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-4 h-4 text-amber-300" />
        <h3 className="text-sm font-bold tracking-wide">Clinical scenario</h3>
        <span className="ml-auto text-[10px] uppercase tracking-wider text-slate-400">demo</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {SCENARIOS.map((s) => {
          const isActive = active === s.id;
          const isBusy = busy === s.id;
          const Icon = s.icon;
          return (
            <button
              key={s.id}
              onClick={() => choose(s.id)}
              data-active={isActive}
              disabled={isBusy}
              className={`flex items-start gap-2 p-2.5 rounded-lg border bg-slate-800/40 text-slate-200 text-left transition-colors disabled:opacity-50 ${TONE[s.tone]}`}
            >
              <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <div className="min-w-0">
                <div className="text-xs font-semibold">{s.label}</div>
                <div className="text-[10px] text-slate-400 leading-tight">{s.description}</div>
              </div>
            </button>
          );
        })}
      </div>
      <p className="mt-3 text-[10px] text-slate-500 leading-snug">
        Drives the live mock-data feed via <code className="bg-slate-800 px-1 rounded">/api/simulation/scenario</code>.
        Layered under temporal projection + PK/PD overlays.
      </p>
    </motion.div>
  );
}
