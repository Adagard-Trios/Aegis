"use client";

import { useEffect, useState } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import { motion } from "framer-motion";
import { Loader2, ShieldCheck, Filter } from "lucide-react";
import { apiGet } from "../../lib/api";

interface AuditRow {
  id: number;
  ts: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip: string | null;
  user_agent: string | null;
}

export default function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const qs = new URLSearchParams();
      if (actionFilter) qs.set("action", actionFilter);
      if (userFilter) qs.set("user_id", userFilter);
      qs.set("limit", "200");
      const r = await apiGet<AuditRow[]>(`/api/admin/audit?${qs}`);
      setRows(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6 max-w-6xl">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
          <ShieldCheck className="w-6 h-6 text-primary" />
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Audit log</h1>
            <p className="text-sm text-muted-foreground mt-1">Immutable record of patient-data access. Admin-only.</p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md p-3 shadow-card flex flex-wrap items-end gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <input
            placeholder="Action (e.g. read, ack, run_now)"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-background border border-border rounded px-2 py-1.5 text-xs"
          />
          <input
            placeholder="User ID"
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="bg-background border border-border rounded px-2 py-1.5 text-xs"
          />
          <button onClick={load} className="ml-auto px-3 py-1.5 rounded-md bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20">
            Apply
          </button>
        </motion.div>

        {err && <div className="bg-rose-500/10 border border-rose-500/30 rounded-md p-3 text-xs text-rose-300">{err}</div>}

        {loading ? (
          <div className="text-sm text-muted-foreground flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Loading…</div>
        ) : rows.length === 0 ? (
          <div className="text-sm text-muted-foreground italic">No audit entries match the filter.</div>
        ) : (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-card border border-border rounded-md shadow-card overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left">Time</th>
                  <th className="px-3 py-2 text-left">User</th>
                  <th className="px-3 py-2 text-left">Action</th>
                  <th className="px-3 py-2 text-left">Resource</th>
                  <th className="px-3 py-2 text-left">ID</th>
                  <th className="px-3 py-2 text-left">IP</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-border/40 hover:bg-muted/30">
                    <td className="px-3 py-1.5 font-mono text-muted-foreground">{r.ts}</td>
                    <td className="px-3 py-1.5">{r.user_id || "—"}</td>
                    <td className="px-3 py-1.5 font-semibold">{r.action}</td>
                    <td className="px-3 py-1.5">{r.resource_type}</td>
                    <td className="px-3 py-1.5 font-mono">{r.resource_id || "—"}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{r.ip || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>
        )}
      </div>
    </DashboardLayout>
  );
}
