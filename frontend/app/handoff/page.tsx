"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { ClipboardList, AlertTriangle, CheckCircle2, Users, Loader2 } from "lucide-react";
import { fetchAlerts, fetchInterpretations, listPatients, type Alert, type InterpretationsMap, type Patient } from "../lib/api";

interface Bundle {
  patient: Patient;
  alerts: Alert[];
  interp: InterpretationsMap;
}

export default function HandoffPage() {
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const patients = await listPatients();
        const targets = patients.length ? patients : [{
          id: "medverse-demo-patient", mrn: null, name: "Default patient",
          dob: null, sex: null, gestational_age_weeks: null, conditions: [],
          assigned_clinician_id: null, created_at: new Date().toISOString(),
        } as Patient];
        const results = await Promise.all(
          targets.map(async (p) => ({
            patient: p,
            alerts: await fetchAlerts({ patient_id: p.id, unacknowledged: true, limit: 20 }).catch(() => []),
            interp: await fetchInterpretations(p.id).catch(() => ({})),
          }))
        );
        if (!cancelled) setBundles(results);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const total = bundles.reduce((acc, b) => acc + b.alerts.length, 0);
  const criticals = bundles.reduce((acc, b) => acc + b.alerts.filter(a => a.severity >= 8).length, 0);

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6 max-w-5xl">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
          <ClipboardList className="w-6 h-6 text-primary" />
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Shift handoff</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {bundles.length} patient{bundles.length === 1 ? "" : "s"} · {total} unacknowledged alert{total === 1 ? "" : "s"}
              {criticals > 0 ? ` · ${criticals} critical` : ""}
            </p>
          </div>
        </motion.div>

        {loading ? (
          <div className="text-sm text-muted-foreground flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Building handoff…</div>
        ) : bundles.length === 0 ? (
          <div className="text-sm text-muted-foreground italic">No patients to hand off.</div>
        ) : (
          <div className="space-y-3">
            {bundles.map((b) => {
              const maxSev = b.alerts.reduce((m, a) => Math.max(m, a.severity), 0);
              const interpMax = Object.values(b.interp).reduce((m, i) => Math.max(m, i.severity_score || 0), 0);
              const overall = Math.max(maxSev, interpMax);
              const tone = overall >= 8 ? "border-rose-500/40 bg-rose-500/5" :
                           overall >= 5 ? "border-orange-500/40 bg-orange-500/5" :
                           overall >= 3 ? "border-amber-500/40 bg-amber-500/5" :
                                          "border-emerald-500/30 bg-emerald-500/5";
              return (
                <motion.div key={b.patient.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`rounded-md border p-4 ${tone}`}>
                  <div className="flex items-center gap-3 mb-3">
                    <Users className="w-5 h-5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold">{b.patient.name}</h3>
                      <p className="text-[10px] text-muted-foreground">
                        MRN {b.patient.mrn || "—"} · severity {overall}/10 · {b.alerts.length} open alert{b.alerts.length === 1 ? "" : "s"}
                      </p>
                    </div>
                    {overall === 0 && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                  </div>

                  {b.alerts.length > 0 && (
                    <div className="mb-2 space-y-1">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Open alerts</div>
                      {b.alerts.slice(0, 5).map((a) => (
                        <div key={a.id} className="flex items-start gap-2 text-xs">
                          <AlertTriangle className={`w-3 h-3 mt-0.5 flex-shrink-0 ${a.severity >= 8 ? "text-rose-400" : a.severity >= 5 ? "text-orange-400" : "text-amber-400"}`} />
                          <span>
                            <span className="font-mono opacity-70">{a.severity}/10</span>{" "}
                            <span className="font-semibold">{a.source}</span> — {a.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {Object.keys(b.interp).length > 0 && (
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Latest agent findings</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-1 mt-1">
                        {Object.entries(b.interp).slice(0, 4).map(([spec, i]) => (
                          <div key={spec} className="text-[11px] text-muted-foreground line-clamp-2">
                            <span className="font-semibold text-foreground">{spec}:</span> {i.interpretation}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
