"use client";

/**
 * What-if treatment-plan panel for /digital-twin.
 *
 * Lets the clinician compose a small treatment sequence (drug + dose +
 * t_min for each step) and POST /api/digital-twin/plan to project the
 * twin's trajectory forward. Renders the predicted trajectory as a line
 * chart (recharts) — HR for the cardiac twin, FHR + uterine activity
 * for the maternal-fetal twin.
 *
 * The simulator runs server-side; the panel is purely UI + display.
 * Each run is persisted with a run_id (visible in /runs) so the
 * clinician can later replay or compare runs.
 */
import { useState } from "react";
import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import {
  FlaskConical, Loader2, Plus, Trash2, AlertOctagon, Heart, Activity,
} from "lucide-react";
import {
  runTwinPlan,
  type TwinName,
  type TwinTreatmentStep,
  type TwinSimulationResponse,
} from "../lib/api";

const DRUG_OPTIONS = [
  { value: "labetalol", label: "Labetalol (β-blocker)" },
  { value: "oxytocin",  label: "Oxytocin (uterotonic)" },
];

const TWIN_OPTIONS: { value: TwinName; label: string }[] = [
  { value: "cardiac", label: "Cardiac" },
  { value: "maternal_fetal", label: "Maternal-fetal" },
];

interface PlanStep extends TwinTreatmentStep {
  id: string;    // local UI id, not sent to server
}

const LINE_TONE: Record<string, string> = {
  hr_bpm: "#a855f7",
  fhr_bpm: "#06b6d4",
  uterine_activity: "#fb923c",
};

function pickChartFields(twin: TwinName): { key: string; label: string; color: string; unit: string }[] {
  if (twin === "cardiac") {
    return [{ key: "hr_bpm", label: "Heart rate", color: LINE_TONE.hr_bpm, unit: "bpm" }];
  }
  return [
    { key: "fhr_bpm", label: "Fetal HR", color: LINE_TONE.fhr_bpm, unit: "bpm" },
    { key: "uterine_activity", label: "Uterine activity", color: LINE_TONE.uterine_activity, unit: "" },
  ];
}

export default function WhatIfPanel({ patientId }: { patientId: string | null }) {
  const [twin, setTwin] = useState<TwinName>("cardiac");
  const [horizonMin, setHorizonMin] = useState(60);
  const [steps, setSteps] = useState<PlanStep[]>([
    { id: crypto.randomUUID(), t_min: 0, drug: "labetalol", dose_mg: 50 },
  ]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TwinSimulationResponse | null>(null);

  const addStep = () =>
    setSteps((s) => [...s, { id: crypto.randomUUID(), t_min: 0, drug: "labetalol", dose_mg: 50 }]);

  const removeStep = (id: string) => setSteps((s) => s.filter((x) => x.id !== id));

  const updateStep = (id: string, patch: Partial<TwinTreatmentStep>) =>
    setSteps((s) => s.map((x) => (x.id === id ? { ...x, ...patch } : x)));

  const trigger = async () => {
    setRunning(true);
    setError(null);
    try {
      const body = {
        twin,
        patient_id: patientId || undefined,
        horizon_min: horizonMin,
        treatment_steps: steps.map(({ id: _id, ...rest }) => rest),
      };
      const r = await runTwinPlan(body);
      setResult(r);
      if (r.status !== "ok") setError(r.error || "Plan run failed");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan run failed");
    } finally {
      setRunning(false);
    }
  };

  const chartFields = pickChartFields(twin);
  const chartData =
    result?.trajectory.map((p) => {
      const row: Record<string, number> = { t_min: Number((p.t_s / 60).toFixed(1)) };
      for (const f of chartFields) {
        const v = p.state?.[f.key];
        if (typeof v === "number") row[f.key] = v;
      }
      return row;
    }) ?? [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border rounded-md p-4 shadow-card space-y-3"
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-fuchsia-500/10 border border-fuchsia-400/30 flex items-center justify-center">
          <FlaskConical className="w-4 h-4 text-fuchsia-300" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-display text-sm font-semibold text-foreground">
            What-if treatment plan
          </h3>
          <p className="text-[11px] text-muted-foreground">
            Project the digital twin forward under a treatment sequence — preview
            HR / FHR / uterine activity before applying.
          </p>
        </div>
        <button
          onClick={trigger}
          disabled={running || steps.length === 0}
          className="flex items-center gap-2 px-3 py-2 rounded-md bg-fuchsia-500/10 hover:bg-fuchsia-500/20 text-fuchsia-200 text-xs font-semibold transition-colors disabled:opacity-50"
        >
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}
          {running ? "Simulating..." : "Run plan"}
        </button>
      </div>

      <div className="flex flex-wrap gap-3 text-xs">
        <label className="flex items-center gap-2">
          <span className="text-muted-foreground">Twin:</span>
          <select
            value={twin}
            onChange={(e) => setTwin(e.target.value as TwinName)}
            className="bg-background border border-border rounded px-2 py-1 text-foreground"
          >
            {TWIN_OPTIONS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <span className="text-muted-foreground">Horizon (min):</span>
          <input
            type="number"
            value={horizonMin}
            onChange={(e) => setHorizonMin(Math.max(5, Math.min(720, Number(e.target.value) || 60)))}
            className="w-16 bg-background border border-border rounded px-2 py-1 text-foreground"
          />
        </label>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
            Treatment steps
          </span>
          <button
            onClick={addStep}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] bg-primary/10 hover:bg-primary/20 text-primary"
          >
            <Plus className="w-3 h-3" /> Add step
          </button>
        </div>
        {steps.map((s) => (
          <div key={s.id} className="flex flex-wrap items-center gap-2 text-xs border border-border/50 rounded p-2">
            <label className="flex items-center gap-1">
              <span className="text-muted-foreground">at t=</span>
              <input
                type="number"
                value={s.t_min}
                onChange={(e) => updateStep(s.id, { t_min: Math.max(0, Number(e.target.value) || 0) })}
                className="w-14 bg-background border border-border rounded px-1.5 py-0.5"
              />
              <span className="text-muted-foreground">min</span>
            </label>
            <select
              value={s.drug}
              onChange={(e) => updateStep(s.id, { drug: e.target.value })}
              className="bg-background border border-border rounded px-2 py-0.5"
            >
              {DRUG_OPTIONS.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
            <label className="flex items-center gap-1">
              <span className="text-muted-foreground">dose:</span>
              <input
                type="number"
                value={s.dose_mg}
                onChange={(e) => updateStep(s.id, { dose_mg: Math.max(1, Number(e.target.value) || 1) })}
                className="w-16 bg-background border border-border rounded px-1.5 py-0.5"
              />
              <span className="text-muted-foreground">mg</span>
            </label>
            <button
              onClick={() => removeStep(s.id)}
              className="ml-auto p-1 rounded hover:bg-rose-500/10 text-rose-300"
              title="Remove step"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>

      {error && (
        <div className="flex items-start gap-2 text-xs text-rose-300 bg-rose-500/10 border border-rose-400/30 rounded p-2">
          <AlertOctagon className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {result && result.status === "ok" && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
            <Heart className="w-3.5 h-3.5" />
            Predicted trajectory
            <span className="ml-auto font-mono normal-case text-muted-foreground/70">
              run_id {result.run_id?.slice(0, 8)}…
            </span>
          </div>
          <div className="h-48 -mx-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                <XAxis dataKey="t_min" stroke="#666" fontSize={10}
                  label={{ value: "minutes", position: "insideBottom", offset: -2, style: { fill: "#888", fontSize: 9 } }} />
                <YAxis stroke="#666" fontSize={10} />
                <Tooltip
                  contentStyle={{ background: "#0a0a0a", border: "1px solid #333", fontSize: 11 }}
                  labelStyle={{ color: "#bbb" }}
                />
                {chartFields.map((f) => (
                  <Line
                    key={f.key}
                    type="monotone"
                    dataKey={f.key}
                    name={f.label}
                    stroke={f.color}
                    dot={false}
                    strokeWidth={2}
                  />
                ))}
                {steps.map((s) => (
                  <ReferenceLine
                    key={s.id}
                    x={s.t_min}
                    stroke="#888"
                    strokeDasharray="2 2"
                    label={{ value: s.drug, fill: "#999", fontSize: 9, position: "top" }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {!result && !error && !running && (
        <p className="text-[11px] text-muted-foreground italic">
          Compose a sequence of timed boluses and click <strong>Run plan</strong>.
          The simulator uses the same Bateman PK/PD constants as the live overlay,
          so what-if predictions match what would actually happen if dosed.
        </p>
      )}
    </motion.div>
  );
}
