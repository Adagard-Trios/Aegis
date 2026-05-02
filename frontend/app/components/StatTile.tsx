"use client";

import { motion } from "framer-motion";
import type { ComponentType } from "react";

interface Props {
  label: string;
  value: string | number;
  unit?: string;
  hint?: string;
  icon?: ComponentType<{ className?: string }>;
  tone?: "default" | "rose" | "amber" | "emerald" | "sky" | "violet";
  loading?: boolean;
  index?: number;
}

const TONE: Record<NonNullable<Props["tone"]>, string> = {
  default: "text-foreground",
  rose: "text-rose-300",
  amber: "text-amber-300",
  emerald: "text-emerald-300",
  sky: "text-sky-300",
  violet: "text-violet-300",
};

export function StatTile({
  label,
  value,
  unit,
  hint,
  icon: Icon,
  tone = "default",
  loading,
  index = 0,
}: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="bg-card border border-border rounded-md p-3 shadow-card"
    >
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
        {Icon && <Icon className="w-3 h-3" />} {label}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`font-display text-2xl font-bold ${TONE[tone]} ${loading ? "opacity-40" : ""}`}>
          {loading ? "--" : value}
        </span>
        {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
      </div>
      {hint && <p className="text-[10px] text-muted-foreground mt-0.5">{hint}</p>}
    </motion.div>
  );
}
