"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { ExpertCard } from "../components/ExpertCard";
import { StatTile } from "../components/StatTile";
import { motion } from "framer-motion";
import { Brain, Activity, Footprints, Gauge, Waves } from "lucide-react";
import { useVestStream } from "../hooks/useVestStream";
import { useActivePatient } from "../hooks/useActivePatient";
import { fetchInterpretations, type InterpretationsMap } from "../lib/api";

export default function NeurologyPage() {
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

  const imu = data?.imu;
  const v = data?.vitals;
  const der = data?.imu_derived;
  const neuroInterp = interp.Neurology || interp.neurology;

  const tremor = der?.tremor;
  const gait = der?.gait;
  const pots = der?.pots;

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">Neurology Module</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Dual-IMU posture/gait, tremor band-power, autonomic HRV, POTS detection.
            {connected ? null : <span className="ml-2 text-amber-400">(stream disconnected)</span>}
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
          <StatTile label="Activity" value={der?.activity_state ?? "--"} tone="violet" icon={Footprints} loading={!data} index={0} />
          <StatTile label="Posture" value={imu?.posture_label ?? "--"} hint={`${imu?.spinal_angle?.toFixed(1) ?? "--"}° spinal`} tone={imu?.poor_posture ? "amber" : "emerald"} icon={Brain} loading={!data} index={1} />
          <StatTile label="HRV (RMSSD)" value={v?.hrv_rmssd?.toFixed(0) ?? "--"} unit="ms" tone="violet" icon={Activity} loading={!data} index={2} />
          <StatTile label="Tremor" value={tremor?.tremor_flag ? "Detected" : "None"} hint={`band ratio ${tremor?.band_ratio?.toFixed(2) ?? "--"}`} tone={tremor?.tremor_flag ? "amber" : "emerald"} icon={Waves} loading={!data} index={3} />
          <StatTile label="POTS" value={pots?.pots_flag ? "Flag" : "Normal"} hint={`HR Δ ${pots?.hr_jump?.toFixed(0) ?? "--"} bpm`} tone={pots?.pots_flag ? "rose" : "emerald"} icon={Gauge} loading={!data} index={4} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <motion.div className="bg-card border border-border rounded-md p-4 shadow-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Gait</h3>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span>Stride count</span><span className="font-mono">{gait?.stride_count ?? "--"}</span></div>
              <div className="flex justify-between"><span>Mean stride (s)</span><span className="font-mono">{gait?.mean_stride_s?.toFixed(2) ?? "--"}</span></div>
              <div className="flex justify-between"><span>Stride CV</span><span className="font-mono">{gait?.stride_cv?.toFixed(2) ?? "--"}</span></div>
              <div className="flex justify-between"><span>Asymmetry</span><span className={`font-mono ${gait?.asymmetry_flag ? "text-amber-400" : "text-emerald-400"}`}>{gait?.asymmetry_flag ? "FLAG" : "ok"}</span></div>
            </div>
          </motion.div>

          <motion.div className="bg-card border border-border rounded-md p-4 shadow-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Tremor band-power</h3>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span>Band power</span><span className="font-mono">{tremor?.band_power?.toFixed(3) ?? "--"}</span></div>
              <div className="flex justify-between"><span>Total power</span><span className="font-mono">{tremor?.total_power?.toFixed(3) ?? "--"}</span></div>
              <div className="flex justify-between"><span>Band ratio</span><span className="font-mono">{tremor?.band_ratio?.toFixed(3) ?? "--"}</span></div>
            </div>
          </motion.div>

          <motion.div className="bg-card border border-border rounded-md p-4 shadow-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Postural orthostatic</h3>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span>HR jump</span><span className="font-mono">{pots?.hr_jump?.toFixed(1) ?? "--"} bpm</span></div>
              <div className="flex justify-between"><span>Angle Δ</span><span className="font-mono">{pots?.angle_delta?.toFixed(1) ?? "--"}°</span></div>
              <div className="flex justify-between"><span>POTS flag</span><span className={`font-mono ${pots?.pots_flag ? "text-rose-400" : "text-emerald-400"}`}>{pots?.pots_flag ? "TRIGGERED" : "ok"}</span></div>
            </div>
          </motion.div>
        </div>

        <ExpertCard title="Neurology AI agent" interpretation={neuroInterp} loading={loadingInterp && !neuroInterp} />
      </div>
    </DashboardLayout>
  );
}
