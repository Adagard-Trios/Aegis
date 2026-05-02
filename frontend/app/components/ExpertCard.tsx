"use client";

import { motion } from "framer-motion";
import { AlertCircle, Brain, Loader2 } from "lucide-react";
import type { Interpretation } from "../lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  normal: "text-emerald-300 border-emerald-400/40 bg-emerald-500/5",
  mild: "text-sky-300 border-sky-400/40 bg-sky-500/5",
  moderate: "text-amber-300 border-amber-400/40 bg-amber-500/5",
  high: "text-orange-300 border-orange-400/40 bg-orange-500/5",
  critical: "text-rose-300 border-rose-400/40 bg-rose-500/5 animate-pulse",
};

function severityClass(s?: string): string {
  if (!s) return SEVERITY_COLOR.normal;
  return SEVERITY_COLOR[s.toLowerCase()] || SEVERITY_COLOR.normal;
}

interface Props {
  title: string;
  interpretation?: Interpretation;
  loading?: boolean;
  emptyHint?: string;
}

export function ExpertCard({ title, interpretation, loading, emptyHint }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-md p-4 shadow-card border ${severityClass(interpretation?.severity)}`}
    >
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-4 h-4" />
        <h3 className="text-xs font-medium uppercase tracking-wider opacity-90">{title}</h3>
        {interpretation?.severity && (
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded-sm bg-white/10 font-semibold uppercase">
            {interpretation.severity}
            {typeof interpretation.severity_score === "number" &&
              ` · ${interpretation.severity_score}/10`}
          </span>
        )}
      </div>
      {loading ? (
        <div className="flex items-center gap-2 text-xs opacity-70">
          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating interpretation…
        </div>
      ) : interpretation ? (
        <>
          <p className="text-sm leading-relaxed whitespace-pre-line">
            {interpretation.interpretation}
          </p>
          <p className="text-[10px] mt-2 opacity-50">
            generated {new Date(interpretation.generated_at).toLocaleString()}
          </p>
        </>
      ) : (
        <div className="flex items-center gap-2 text-xs opacity-70">
          <AlertCircle className="w-3.5 h-3.5" />
          {emptyHint || "Awaiting first interpretation from the agent worker."}
        </div>
      )}
    </motion.div>
  );
}
