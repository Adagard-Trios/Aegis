"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Activity, Clock, Heart, Wind, Waves, RefreshCw } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchHistory, HistoryPoint } from "../lib/api";

type Resolution = "1m" | "1h";

interface Panel {
  key: "hr" | "spo2" | "br" | "hrv";
  label: string;
  unit: string;
  color: string;
  icon: React.ComponentType<{ className?: string }>;
}

const PANELS: Panel[] = [
  { key: "hr", label: "Heart rate", unit: "bpm", color: "#ef4444", icon: Heart },
  { key: "spo2", label: "SpO₂", unit: "%", color: "#3b82f6", icon: Activity },
  { key: "br", label: "Respiratory rate", unit: "br/min", color: "#10b981", icon: Wind },
  { key: "hrv", label: "HRV (RMSSD)", unit: "ms", color: "#a855f7", icon: Waves },
];

function formatTs(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString([], { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function HistoryPage() {
  const [resolution, setResolution] = useState<Resolution>("1h");
  const [series, setSeries] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(res: Resolution) {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHistory({ resolution: res, limit: 500 });
      setSeries(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load history");
      setSeries([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(resolution);
  }, [resolution]);

  const hasData = series.some((p) => PANELS.some((panel) => p[panel.key] != null));

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-center justify-between gap-4"
        >
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Session History</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Vital trends from the backend's /api/history endpoint. Sourced from Timescale
              continuous aggregates when <code>MEDVERSE_DB_URL</code> is set; otherwise bucketed
              from SQLite.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex rounded-md border border-border overflow-hidden">
              {(["1m", "1h"] as Resolution[]).map((r) => (
                <button
                  key={r}
                  onClick={() => setResolution(r)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    resolution === r
                      ? "bg-primary text-primary-foreground"
                      : "bg-background text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {r === "1m" ? "1 min" : "1 hour"}
                </button>
              ))}
            </div>
            <button
              onClick={() => load(resolution)}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border bg-background text-xs font-medium hover:bg-muted disabled:opacity-60"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </motion.div>

        {error && (
          <div className="text-sm text-red-500 bg-red-500/10 rounded px-3 py-2 border border-red-500/30">
            {error}
          </div>
        )}

        {!loading && !hasData && !error && (
          <div className="bg-card border border-border rounded-md p-6 text-center">
            <Clock className="w-5 h-5 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              No aggregated vitals yet. Stream data for a minute or two then refresh.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {PANELS.map((panel, i) => (
            <motion.div
              key={panel.key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i }}
              className="bg-card border border-border rounded-md p-4 shadow-card"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <panel.icon className="w-4 h-4" style={{ color: panel.color }} />
                  <h3 className="text-sm font-semibold text-foreground">{panel.label}</h3>
                </div>
                <span className="text-[10px] text-muted-foreground font-mono uppercase">
                  {panel.unit} · {resolution === "1m" ? "per-minute" : "per-hour"}
                </span>
              </div>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series} margin={{ top: 5, right: 10, bottom: 0, left: -10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.15)" />
                    <XAxis
                      dataKey="ts"
                      tickFormatter={formatTs}
                      stroke="currentColor"
                      tick={{ fontSize: 10, fill: "currentColor", opacity: 0.6 }}
                      minTickGap={32}
                    />
                    <YAxis
                      stroke="currentColor"
                      tick={{ fontSize: 10, fill: "currentColor", opacity: 0.6 }}
                      domain={["auto", "auto"]}
                      width={36}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(15,23,42,0.9)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      labelFormatter={formatTs}
                      formatter={(value: number | string) => {
                        if (value == null) return "—";
                        return [`${value} ${panel.unit}`, panel.label];
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey={panel.key}
                      stroke={panel.color}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
