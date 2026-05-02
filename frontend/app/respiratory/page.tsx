"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { ExpertCard } from "../components/ExpertCard";
import { StatTile } from "../components/StatTile";
import { motion } from "framer-motion";
import { Wind, Activity, Volume2, Gauge, Waves, AlertCircle } from "lucide-react";
import { useVestStream } from "../hooks/useVestStream";
import { useActivePatient } from "../hooks/useActivePatient";
import { fetchInterpretations, type InterpretationsMap } from "../lib/api";

export default function RespiratoryPage() {
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

  const v = data?.vitals;
  const a = data?.audio;
  const pulmInterp = interp.Pulmonary || interp.pulmonary;
  const waveformOn = !!data?.waveform;

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">Respiratory Module</h1>
          <p className="text-sm text-muted-foreground mt-1">
            I²S acoustic + PPG-derived respiratory rate, lung-sound classification.
            {connected ? null : <span className="ml-2 text-amber-400">(stream disconnected)</span>}
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile label="SpO₂" value={v?.spo2?.toFixed(1) ?? "--"} unit="%" tone="sky" icon={Activity} loading={!data} index={0} />
          <StatTile label="Resp rate" value={v?.breathing_rate?.toFixed(0) ?? "--"} unit="rpm" tone="emerald" icon={Wind} loading={!data} index={1} />
          <StatTile label="Audio (analog)" value={a?.analog_rms?.toFixed(0) ?? "--"} unit="rms" tone="violet" icon={Volume2} loading={!data} index={2} />
          <StatTile label="Audio (digital)" value={a?.digital_rms?.toFixed(0) ?? "--"} unit="rms" tone="violet" icon={Volume2} loading={!data} index={3} />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Waves className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Acoustic waveform
            </h3>
            {waveformOn ? (
              <span className="ml-auto text-[10px] px-2 py-0.5 rounded-sm bg-emerald-500/10 text-emerald-400 font-semibold">LIVE</span>
            ) : (
              <span className="ml-auto text-[10px] px-2 py-0.5 rounded-sm bg-amber-500/10 text-amber-400 font-semibold">OFF</span>
            )}
          </div>
          {waveformOn ? (
            <p className="text-xs text-muted-foreground">
              {data?.waveform?.audio?.length ?? 0} samples @ {data?.waveform?.fs ?? 0} Hz
            </p>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertCircle className="w-3.5 h-3.5" />
              Set <code className="px-1 bg-muted rounded">MEDVERSE_INCLUDE_WAVEFORM=true</code> on the
              backend to stream the raw 800-sample buffers.
            </div>
          )}
        </motion.div>

        <ExpertCard title="Pulmonology AI agent" interpretation={pulmInterp} loading={loadingInterp && !pulmInterp} />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile label="Hypoxia" value={(v?.spo2 ?? 100) < 92 ? "Detected" : "None"} hint={`SpO₂ ${v?.spo2?.toFixed(0) ?? "--"}%`} tone={(v?.spo2 ?? 100) < 92 ? "rose" : "emerald"} icon={Gauge} index={0} />
          <StatTile label="Tachypnea" value={(v?.breathing_rate ?? 0) > 20 ? "Yes" : "No"} hint={`RR ${v?.breathing_rate?.toFixed(0) ?? "--"} rpm`} tone={(v?.breathing_rate ?? 0) > 20 ? "amber" : "emerald"} icon={Wind} index={1} />
          <StatTile label="Apnea risk" value="N/A" hint="needs sleep stage" index={2} />
          <StatTile label="Acoustic flag" value={(a?.digital_rms ?? 0) > 1500 ? "Loud" : "Quiet"} tone={(a?.digital_rms ?? 0) > 1500 ? "amber" : "emerald"} index={3} />
        </div>
      </div>
    </DashboardLayout>
  );
}
