"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { LiveECGMonitor } from "../components/LiveECGMonitor";
import { ExpertCard } from "../components/ExpertCard";
import { StatTile } from "../components/StatTile";
import { motion } from "framer-motion";
import { Heart, Activity, Waves, Gauge, Zap, Wind } from "lucide-react";
import { useVestStream } from "../hooks/useVestStream";
import { useActivePatient } from "../hooks/useActivePatient";
import { fetchInterpretations, type InterpretationsMap } from "../lib/api";

export default function CardiologyPage() {
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
        /* offline-tolerant */
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
  const e = data?.ecg;
  const activity = data?.imu_derived?.activity_state;

  const cardiologyInterp = interp.Cardiology || interp.cardiology;

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">Cardiology Module</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time cardiovascular monitoring via 5-pad dual-ECG configuration.
            {connected ? null : <span className="ml-2 text-amber-400">(stream disconnected)</span>}
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <StatTile label="Heart rate" value={v?.heart_rate?.toFixed(0) ?? "--"} unit="bpm" tone="rose" icon={Heart} loading={!data} index={0} />
          <StatTile label="ECG HR" value={e?.ecg_hr?.toFixed(0) ?? "--"} unit="bpm" tone="rose" icon={Activity} loading={!data} index={1} />
          <StatTile label="HRV (RMSSD)" value={v?.hrv_rmssd?.toFixed(0) ?? "--"} unit="ms" tone="violet" icon={Waves} loading={!data} index={2} />
          <StatTile label="Perfusion idx" value={v?.perfusion_index?.toFixed(2) ?? "--"} unit="%" tone="sky" icon={Gauge} loading={!data} index={3} />
          <StatTile label="Signal" value={v?.signal_quality ?? "--"} tone="emerald" icon={Zap} loading={!data} index={4} />
          <StatTile label="Activity" value={activity ?? "--"} tone="amber" icon={Wind} loading={!data} index={5} />
        </div>

        <LiveECGMonitor />

        <ExpertCard
          title="Cardiology AI agent"
          interpretation={cardiologyInterp}
          loading={loadingInterp && !cardiologyInterp}
        />
      </div>
    </DashboardLayout>
  );
}
