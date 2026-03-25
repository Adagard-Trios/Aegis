"use client";

import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { History, Clock, AlertCircle, CheckCircle2 } from "lucide-react";

export default function HistoryPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">
            Session History
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Past monitoring sessions, alerts, and trend analysis
          </p>
        </motion.div>

        {/* Current Session */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Current Session
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-sm bg-accent/10 text-accent font-semibold ml-auto">
              ACTIVE
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-muted/50 rounded px-3 py-2">
              <p className="text-[10px] text-muted-foreground uppercase">Duration</p>
              <p className="text-sm font-bold text-foreground font-display">Active</p>
            </div>
            <div className="bg-muted/50 rounded px-3 py-2">
              <p className="text-[10px] text-muted-foreground uppercase">Alerts</p>
              <p className="text-sm font-bold text-accent font-display">0</p>
            </div>
            <div className="bg-muted/50 rounded px-3 py-2">
              <p className="text-[10px] text-muted-foreground uppercase">Data Points</p>
              <p className="text-sm font-bold text-foreground font-display">Streaming</p>
            </div>
            <div className="bg-muted/50 rounded px-3 py-2">
              <p className="text-[10px] text-muted-foreground uppercase">Status</p>
              <p className="text-sm font-bold text-accent font-display">All Clear</p>
            </div>
          </div>
        </motion.div>

        {/* Past Sessions */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-4">
            <History className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Recent Sessions
            </h3>
          </div>
          <div className="space-y-3">
            {[
              { date: "Today", duration: "Active", alerts: 0, status: "Monitoring" },
              { date: "Yesterday", duration: "4h 32m", alerts: 0, status: "Completed" },
              { date: "Mar 20", duration: "6h 15m", alerts: 1, status: "Completed" },
              { date: "Mar 19", duration: "3h 48m", alerts: 0, status: "Completed" },
              { date: "Mar 18", duration: "5h 22m", alerts: 0, status: "Completed" },
            ].map((s, i) => (
              <motion.div
                key={s.date}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.05 }}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <div className="flex items-center gap-3">
                  {s.alerts === 0 ? (
                    <CheckCircle2 className="w-4 h-4 text-accent" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-warning" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-foreground">{s.date}</p>
                    <p className="text-[10px] text-muted-foreground">{s.duration}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">{s.alerts} alerts</p>
                  <p className="text-[10px] text-accent font-semibold uppercase">{s.status}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
