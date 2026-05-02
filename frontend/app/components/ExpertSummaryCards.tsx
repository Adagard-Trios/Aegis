"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Heart, Wind, Baby, Eye, Stethoscope, Brain, Loader2, RefreshCw } from "lucide-react";
import { fetchInterpretations, runAgentNow, type InterpretationsMap } from "../lib/api";
import { useActivePatient } from "../hooks/useActivePatient";

const META: Record<string, { icon: React.ElementType; color: string }> = {
  Cardiology:        { icon: Heart,       color: "#ef4444" },
  Pulmonary:         { icon: Wind,        color: "#10b981" },
  Neurology:         { icon: Brain,       color: "#8b5cf6" },
  Dermatology:       { icon: Stethoscope, color: "#f59e0b" },
  Obstetrics:        { icon: Baby,        color: "#ec4899" },
  Ocular:            { icon: Eye,         color: "#06b6d4" },
  "General Physician": { icon: Stethoscope, color: "#3b82f6" },
};

const ORDER = ["Cardiology", "Pulmonary", "Neurology", "Dermatology", "Obstetrics", "Ocular", "General Physician"];

const SEVERITY_TONE: Record<string, string> = {
  normal: "bg-emerald-500/10 text-emerald-300",
  mild: "bg-sky-500/10 text-sky-300",
  moderate: "bg-amber-500/10 text-amber-300",
  high: "bg-orange-500/10 text-orange-300",
  critical: "bg-rose-500/10 text-rose-300 animate-pulse",
};

export function ExpertSummaryCards() {
  const { patientId } = useActivePatient();
  const [interp, setInterp] = useState<InterpretationsMap>({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = async () => {
    try {
      const r = await fetchInterpretations(patientId || undefined);
      setInterp(r);
    } catch {
      /* offline */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
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

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Expert agent summaries
        </h3>
        <button
          onClick={triggerRun}
          disabled={running}
          className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted hover:bg-muted/70 text-[10px] font-semibold transition-colors disabled:opacity-50"
        >
          {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
          Run now
        </button>
      </div>

      {loading && Object.keys(interp).length === 0 ? (
        <div className="text-xs text-muted-foreground italic flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading interpretations…
        </div>
      ) : Object.keys(interp).length === 0 ? (
        <div className="text-xs text-muted-foreground italic">
          No interpretations yet — the agent worker runs every minute, or click <strong>Run now</strong>.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {ORDER.map((spec, i) => {
            const data = interp[spec] || interp[spec.toLowerCase()];
            if (!data) return null;
            const meta = META[spec] || { icon: Stethoscope, color: "#64748b" };
            const Icon = meta.icon;
            const sev = (data.severity || "normal").toLowerCase();
            return (
              <motion.div
                key={spec}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.3 }}
                className="bg-card border border-border rounded-lg p-4 shadow-card hover:shadow-card-hover transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-md flex items-center justify-center" style={{ backgroundColor: `${meta.color}15` }}>
                      <Icon className="w-4 h-4" style={{ color: meta.color }} />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-foreground">{spec}</h4>
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(data.generated_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-sm ${SEVERITY_TONE[sev] || SEVERITY_TONE.normal}`}>
                    {data.severity} · {data.severity_score}/10
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">
                  {data.interpretation}
                </p>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
