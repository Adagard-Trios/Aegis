"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Stethoscope, AlertCircle, CheckCircle2, BarChart3, RefreshCw, Loader2 } from "lucide-react";
import { useActivePatient } from "../hooks/useActivePatient";
import {
  fetchInterpretations,
  runAgentNow,
  type InterpretationsMap,
} from "../lib/api";

const SPECIALTIES = [
  "Cardiology",
  "Pulmonary",
  "Neurology",
  "Dermatology",
  "Obstetrics",
  "Ocular",
  "General Physician",
];

const SEVERITY_TONE: Record<string, string> = {
  normal: "bg-emerald-500/10 text-emerald-300 border-emerald-400/30",
  mild: "bg-sky-500/10 text-sky-300 border-sky-400/30",
  moderate: "bg-amber-500/10 text-amber-300 border-amber-400/30",
  high: "bg-orange-500/10 text-orange-300 border-orange-400/30",
  critical: "bg-rose-500/10 text-rose-300 border-rose-400/30 animate-pulse",
};

export default function DiagnosticsPage() {
  const { patientId } = useActivePatient();
  const [interp, setInterp] = useState<InterpretationsMap>({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const r = await fetchInterpretations(patientId || undefined);
      setInterp(r);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    load();
    const id = setInterval(() => !cancelled && load(), 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  const triggerRun = async () => {
    setRunning(true);
    try {
      await runAgentNow(patientId || undefined);
      await load();
    } finally {
      setRunning(false);
    }
  };

  const totalScore = Object.values(interp).reduce((acc, i) => acc + (i.severity_score || 0), 0);
  const maxSev = Object.values(interp).reduce((acc, i) => Math.max(acc, i.severity_score || 0), 0);
  const overall =
    maxSev >= 8 ? { label: "Critical", tone: SEVERITY_TONE.critical, icon: AlertCircle } :
    maxSev >= 5 ? { label: "Attention", tone: SEVERITY_TONE.high, icon: AlertCircle } :
    maxSev >= 3 ? { label: "Watch", tone: SEVERITY_TONE.moderate, icon: AlertCircle } :
                  { label: "All clear", tone: SEVERITY_TONE.normal, icon: CheckCircle2 };
  const OverallIcon = overall.icon;

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Diagnostics</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Cross-specialty agent fan-out, severity-weighted, refreshed every 30 s.
            </p>
          </div>
          <button
            onClick={triggerRun}
            disabled={running}
            className="ml-auto flex items-center gap-2 px-3 py-2 rounded-md bg-primary/10 hover:bg-primary/20 text-primary text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Run all agents now
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className={`rounded-md p-5 border flex items-center gap-3 ${overall.tone}`}
        >
          <OverallIcon className="w-6 h-6" />
          <div>
            <div className="text-xs uppercase tracking-wider opacity-70">Overall status</div>
            <div className="text-2xl font-display font-bold">{overall.label}</div>
            <div className="text-[11px] opacity-70">
              cumulative severity {totalScore} · max {maxSev}
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Per-specialty severity
            </h3>
          </div>
          <div className="space-y-3">
            {SPECIALTIES.map((s) => {
              const i = interp[s] || interp[s.toLowerCase()];
              const score = i?.severity_score ?? 0;
              const sev = (i?.severity || "normal").toLowerCase();
              return (
                <div key={s}>
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Stethoscope className="w-3.5 h-3.5" />
                      <span className="font-medium">{s}</span>
                      {i && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-sm font-semibold uppercase border ${SEVERITY_TONE[sev]}`}>
                          {i.severity}
                        </span>
                      )}
                    </div>
                    <span className="font-mono text-muted-foreground">
                      {i ? `${score}/10` : "no data"}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 bg-muted/40 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        score >= 8 ? "bg-rose-500" :
                        score >= 5 ? "bg-orange-500" :
                        score >= 3 ? "bg-amber-500" :
                                     "bg-emerald-500"
                      }`}
                      style={{ width: `${(score / 10) * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          {loading && (
            <p className="mt-3 text-[11px] text-muted-foreground italic">Loading interpretations…</p>
          )}
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
            Latest findings
          </h3>
          <div className="space-y-2">
            {SPECIALTIES.filter((s) => interp[s] || interp[s.toLowerCase()]).map((s) => {
              const i = interp[s] || interp[s.toLowerCase()];
              return (
                <div key={s} className="text-xs border-l-2 border-primary/40 pl-3 py-1">
                  <div className="font-semibold text-foreground">{s}</div>
                  <div className="text-muted-foreground line-clamp-2">{i.interpretation}</div>
                  <div className="text-[10px] text-muted-foreground/60 mt-0.5">
                    {new Date(i.generated_at).toLocaleString()}
                  </div>
                </div>
              );
            })}
            {Object.keys(interp).length === 0 && (
              <p className="text-xs text-muted-foreground italic">
                No interpretations yet — click <strong>Run all agents now</strong> or wait for the
                background worker to populate the table.
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
