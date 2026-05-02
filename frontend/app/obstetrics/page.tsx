"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { ExpertCard } from "../components/ExpertCard";
import { motion } from "framer-motion";
import { Baby, Heart, Activity, AlertCircle, Waves, Thermometer } from "lucide-react";
import { useVestStream } from "../hooks/useVestStream";
import { useActivePatient } from "../hooks/useActivePatient";
import { fetchInterpretations, type InterpretationsMap } from "../lib/api";

interface DawesRedman {
  fhr_baseline?: number;
  decelerations?: string;
  reactivity?: string;
  short_term_variability?: number;
  long_term_variability?: number;
  classification?: string;
}

export default function ObstetricsPage() {
  const { data, connected } = useVestStream();
  const { patientId } = useActivePatient();
  const [interp, setInterp] = useState<InterpretationsMap>({});
  const [loadingInterp, setLoadingInterp] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const r = await fetchInterpretations(patientId || undefined);
        if (!cancelled) setInterp(r);
      } catch {
        /* offline */
      } finally {
        if (!cancelled) setLoadingInterp(false);
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [patientId]);

  const obInterp = interp.Obstetrics || interp.obstetrics || interp.Gynecology;
  const dr = (data?.fetal as { dawes_redman?: DawesRedman } | undefined)?.dawes_redman;
  const kicks = data?.fetal?.kicks || [false, false, false, false];
  const contractions = data?.fetal?.contractions || [false, false];
  const heartTones = data?.fetal?.heart_tones || [false, false];

  const fhr = dr?.fhr_baseline ?? (heartTones.some(Boolean) ? 145 : 140);
  const accelerations = kicks.some(Boolean) ? "Present (Kick)" : "None";
  const decelerations = dr?.decelerations || "None";
  const reactivity = dr?.reactivity || "Reactive";
  const stv = dr?.short_term_variability;
  const ctgClass = dr?.classification || (contractions.some(Boolean) ? "Category II" : "Category I");

  const mhr = data?.vitals?.heart_rate?.toFixed(0) || "--";
  const mtemp = data?.temperature?.cervical?.toFixed(1) || "--";

  const isReactive = reactivity?.toLowerCase().includes("react") && !reactivity?.toLowerCase().includes("non");
  const hasLateDecel = decelerations?.toLowerCase().includes("late");

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">Obstetrics & Gynecology</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Foetal monitoring, CTG analysis, Dawes-Redman criteria & maternal vitals.
            {connected ? null : <span className="ml-2 text-amber-400">(stream disconnected)</span>}
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
          {[
            { label: "Foetal HR", value: String(fhr), unit: "BPM", icon: Baby, alert: hasLateDecel },
            { label: "Reactivity", value: reactivity, unit: "", icon: Activity, alert: !isReactive },
            { label: "Accelerations", value: accelerations, unit: "", icon: Waves, alert: false },
            { label: "Uterine activity", value: contractions.some(Boolean) ? "Active" : "None", unit: "", icon: AlertCircle, alert: contractions.some(Boolean) },
            { label: "Maternal HR", value: mhr, unit: "BPM", icon: Heart, alert: false },
            { label: "Maternal temp", value: mtemp, unit: "°C", icon: Thermometer, alert: false },
          ].map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className={`border rounded-md p-3 shadow-card text-center transition-colors duration-300 ${
                m.alert ? "bg-amber-500/10 border-amber-400/40" : "bg-card border-border"
              }`}
            >
              <m.icon className={`w-4 h-4 mx-auto mb-1 ${m.alert ? "text-amber-400" : "text-primary"}`} />
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{m.label}</p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="font-display text-xl font-bold text-foreground">{m.value}</span>
                {m.unit && <span className="text-xs text-muted-foreground">{m.unit}</span>}
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <div className="flex items-center gap-2 mb-3">
            <Baby className="w-4 h-4 text-pink-500" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">CTG Assessment (Dawes-Redman)</h3>
            <span className={`text-[10px] px-2 py-0.5 rounded-sm font-semibold ml-auto ${
              hasLateDecel ? "bg-rose-500/10 text-rose-400 animate-pulse" :
              isReactive ? "bg-emerald-500/10 text-emerald-400" :
                           "bg-amber-500/10 text-amber-400"
            }`}>
              {hasLateDecel ? "ATTENTION" : isReactive ? "REASSURING" : "WATCH"}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Baseline FHR", value: `${fhr} BPM`, status: fhr >= 110 && fhr <= 160 ? "Normal (110–160)" : "Out of range" },
              { label: "Reactivity", value: reactivity, status: isReactive ? "Reactive" : "Non-reactive" },
              { label: "Accelerations", value: accelerations, status: kicks.some(Boolean) ? "Present" : "Quiet" },
              { label: "Decelerations", value: decelerations, status: hasLateDecel ? "Late decel" : "None" },
              { label: "Uterine activity", value: contractions.some(Boolean) ? "Active" : "Quiet", status: `${contractions.filter(Boolean).length}/2 sites` },
              { label: "CTG class", value: ctgClass, status: ctgClass.includes("II") ? "Suspicious" : "Normal" },
              { label: "STV (ms)", value: stv ? stv.toFixed(1) : "—", status: stv && stv < 3 ? "Low" : "Normal" },
              { label: "Heart tones", value: `${heartTones.filter(Boolean).length}/2`, status: heartTones.some(Boolean) ? "Audible" : "Silent" },
            ].map((d) => (
              <div key={d.label} className="bg-muted/40 rounded px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{d.label}</p>
                <p className="text-xs font-semibold text-foreground">{d.value}</p>
                <p className="text-[9px] text-muted-foreground uppercase mt-0.5">{d.status}</p>
              </div>
            ))}
          </div>
        </motion.div>

        <ExpertCard title="OB/GYN AI agent" interpretation={obInterp} loading={loadingInterp && !obInterp} />
      </div>
    </DashboardLayout>
  );
}
