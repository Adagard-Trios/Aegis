"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";
import { fetchInterpretations, fetchAlerts, type InterpretationsMap, type Alert } from "../lib/api";
import { useActivePatient } from "../hooks/useActivePatient";

export function SystemSummary() {
  const { patientId } = useActivePatient();
  const [interp, setInterp] = useState<InterpretationsMap>({});
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [i, a] = await Promise.all([
          fetchInterpretations(patientId || undefined),
          fetchAlerts({ patient_id: patientId || undefined, unacknowledged: true, limit: 50 }),
        ]);
        if (!cancelled) {
          setInterp(i);
          setAlerts(a);
        }
      } catch { /* offline */ }
    };
    load();
    const id = setInterval(load, 15_000);
    return () => { cancelled = true; clearInterval(id); };
  }, [patientId]);

  const scores = Object.values(interp).map((v) => v.severity_score || 0);
  const max = scores.length ? Math.max(...scores) : 0;
  const criticals = alerts.filter((a) => a.severity >= 8).length;
  const highs = alerts.filter((a) => a.severity >= 5 && a.severity < 8).length;

  let status: "clear" | "watch" | "attention" | "critical" = "clear";
  if (criticals > 0 || max >= 8) status = "critical";
  else if (highs > 0 || max >= 5) status = "attention";
  else if (max >= 3) status = "watch";

  const meta = {
    clear: { Icon: CheckCircle2, color: "text-emerald-400", label: "All Clear", border: "border-emerald-500/30 bg-emerald-500/5" },
    watch: { Icon: Activity, color: "text-sky-400", label: "Watch", border: "border-sky-500/30 bg-sky-500/5" },
    attention: { Icon: AlertCircle, color: "text-amber-400", label: "Attention", border: "border-amber-500/30 bg-amber-500/5" },
    critical: { Icon: AlertTriangle, color: "text-rose-400", label: "Critical", border: "border-rose-500/40 bg-rose-500/10 animate-pulse" },
  }[status];

  const gp = interp["General Physician"] || interp.general_physician;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`rounded-md border p-5 shadow-card ${meta.border}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-display font-semibold text-foreground text-sm tracking-wide">
          System summary
        </h3>
        <div className={`flex items-center gap-1.5 ${meta.color}`}>
          <meta.Icon className="w-4 h-4" />
          <span className="text-xs font-semibold uppercase tracking-wider">{meta.label}</span>
        </div>
      </div>

      <p className="text-sm text-muted-foreground leading-relaxed mb-3">
        {gp?.interpretation
          ? gp.interpretation
          : "Awaiting first general-physician interpretation. Background agent runs every 60 s."}
      </p>

      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="bg-muted/40 rounded px-3 py-2">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Active alerts</p>
          <p className={`text-sm font-bold ${alerts.length > 0 ? "text-amber-400" : "text-emerald-400"}`}>{alerts.length}</p>
        </div>
        <div className="bg-muted/40 rounded px-3 py-2">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Critical</p>
          <p className={`text-sm font-bold ${criticals > 0 ? "text-rose-400" : "text-emerald-400"}`}>{criticals}</p>
        </div>
        <div className="bg-muted/40 rounded px-3 py-2">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Max severity</p>
          <p className="text-sm font-bold text-foreground">{max}/10</p>
        </div>
      </div>
    </motion.div>
  );
}
