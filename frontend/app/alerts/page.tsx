"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Filter, Loader2 } from "lucide-react";
import { fetchAlerts, acknowledgeAlert, type Alert } from "../lib/api";
import { useActivePatient } from "../hooks/useActivePatient";

const SEVERITY: Record<number, { tone: string; label: string }> = {
  10: { tone: "border-rose-500/50 bg-rose-500/10 text-rose-200", label: "Emergency" },
  9: { tone: "border-rose-500/50 bg-rose-500/10 text-rose-200 animate-pulse", label: "Critical" },
  8: { tone: "border-rose-500/40 bg-rose-500/5 text-rose-200", label: "Critical" },
  7: { tone: "border-orange-500/40 bg-orange-500/5 text-orange-200", label: "High" },
  6: { tone: "border-orange-500/40 bg-orange-500/5 text-orange-200", label: "High" },
  5: { tone: "border-amber-500/40 bg-amber-500/5 text-amber-200", label: "Moderate" },
  4: { tone: "border-amber-500/40 bg-amber-500/5 text-amber-200", label: "Watch" },
  3: { tone: "border-sky-500/40 bg-sky-500/5 text-sky-200", label: "Watch" },
  2: { tone: "border-slate-500/40 bg-slate-500/5 text-slate-200", label: "Info" },
  1: { tone: "border-slate-500/40 bg-slate-500/5 text-slate-200", label: "Info" },
};

function tone(sev: number): string {
  return (SEVERITY[sev] || SEVERITY[1]).tone;
}
function label(sev: number): string {
  return (SEVERITY[sev] || SEVERITY[1]).label;
}

export default function AlertsPage() {
  const { patientId } = useActivePatient();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAcked, setShowAcked] = useState(false);
  const [acking, setAcking] = useState<number | null>(null);
  const [note, setNote] = useState<Record<number, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetchAlerts({ patient_id: patientId || undefined, unacknowledged: !showAcked, limit: 200 });
      setAlerts(r);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 5_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, showAcked]);

  const ack = async (id: number) => {
    setAcking(id);
    try {
      await acknowledgeAlert(id, note[id] || "");
      setNote((n) => ({ ...n, [id]: "" }));
      await load();
    } finally {
      setAcking(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6 max-w-4xl">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Alerts</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Threshold-based clinical alerts, refreshed every 5 s.
              {patientId && <span className="ml-2">Patient: <code className="px-1 bg-muted rounded">{patientId}</code></span>}
            </p>
          </div>
          <button
            onClick={() => setShowAcked(!showAcked)}
            className="ml-auto flex items-center gap-2 px-3 py-2 rounded-md bg-muted hover:bg-muted/70 text-xs font-semibold transition-colors"
          >
            <Filter className="w-3.5 h-3.5" />
            {showAcked ? "Hide acknowledged" : "Show acknowledged"}
          </button>
        </motion.div>

        {loading && alerts.length === 0 && (
          <div className="text-sm text-muted-foreground flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading alerts…
          </div>
        )}

        {!loading && alerts.length === 0 && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-md p-6 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <p className="text-emerald-200 font-semibold">No alerts</p>
            <p className="text-emerald-200/70 text-xs mt-1">Vitals are within thresholds.</p>
          </div>
        )}

        <div className="space-y-3">
          {alerts.map((a) => (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`rounded-md border p-4 ${tone(a.severity)}`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-white/10">{label(a.severity)} · {a.severity}/10</span>
                    <span className="text-[10px] font-mono opacity-70">{a.source}</span>
                    <span className="text-[10px] opacity-50 ml-auto">{new Date(a.created_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-1 text-sm">{a.message}</p>
                  {a.acknowledged_at && (
                    <p className="mt-1 text-[10px] opacity-70">
                      ✓ Acknowledged by {a.acknowledged_by} at {new Date(a.acknowledged_at).toLocaleString()}
                    </p>
                  )}
                  {!a.acknowledged_at && (
                    <div className="mt-3 flex gap-2">
                      <input
                        placeholder="Note (optional)"
                        value={note[a.id] || ""}
                        onChange={(e) => setNote((n) => ({ ...n, [a.id]: e.target.value }))}
                        className="flex-1 bg-black/30 border border-white/10 rounded px-2 py-1.5 text-xs"
                      />
                      <button
                        onClick={() => ack(a.id)}
                        disabled={acking === a.id}
                        className="px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/20 text-xs font-semibold flex items-center gap-1 disabled:opacity-50"
                      >
                        {acking === a.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                        Acknowledge
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
