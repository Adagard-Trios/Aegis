"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Plus, User, Loader2, X } from "lucide-react";
import { listPatients, createPatient, type Patient } from "../lib/api";
import { useActivePatient } from "../hooks/useActivePatient";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", mrn: "", dob: "", sex: "", gestational_age_weeks: "" });
  const { patientId, setPatientId } = useActivePatient();
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await listPatients();
      setPatients(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setErr(null);
    try {
      const ga = form.gestational_age_weeks ? parseInt(form.gestational_age_weeks) : undefined;
      const p = await createPatient({
        name: form.name,
        mrn: form.mrn || undefined,
        dob: form.dob || undefined,
        sex: form.sex || undefined,
        gestational_age_weeks: ga,
      });
      setPatients((cur) => [p, ...cur]);
      setShowForm(false);
      setForm({ name: "", mrn: "", dob: "", sex: "", gestational_age_weeks: "" });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6 max-w-5xl">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Patients</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {patients.length === 0 && !loading ? "No patients yet — create one to scope telemetry, alerts, and interpretations." : `${patients.length} patient${patients.length === 1 ? "" : "s"}`}
            </p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="ml-auto flex items-center gap-2 px-3 py-2 rounded-md bg-primary/10 hover:bg-primary/20 text-primary text-sm font-semibold transition-colors"
          >
            <Plus className="w-4 h-4" /> New patient
          </button>
        </motion.div>

        {err && <div className="bg-rose-500/10 border border-rose-500/30 rounded-md p-3 text-xs text-rose-300">{err}</div>}

        {showForm && (
          <motion.form initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} onSubmit={submit} className="bg-card border border-border rounded-md p-4 shadow-card space-y-3">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">Create patient</h3>
              <button type="button" onClick={() => setShowForm(false)} className="ml-auto text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input className="bg-background border border-border rounded px-3 py-2 text-sm" placeholder="Name *" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <input className="bg-background border border-border rounded px-3 py-2 text-sm" placeholder="MRN" value={form.mrn} onChange={(e) => setForm({ ...form, mrn: e.target.value })} />
              <input className="bg-background border border-border rounded px-3 py-2 text-sm" placeholder="DOB (YYYY-MM-DD)" value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} />
              <select className="bg-background border border-border rounded px-3 py-2 text-sm" value={form.sex} onChange={(e) => setForm({ ...form, sex: e.target.value })}>
                <option value="">Sex…</option>
                <option value="F">F</option>
                <option value="M">M</option>
                <option value="X">X</option>
              </select>
              <input className="bg-background border border-border rounded px-3 py-2 text-sm" placeholder="Gestational age (weeks, optional)" type="number" value={form.gestational_age_weeks} onChange={(e) => setForm({ ...form, gestational_age_weeks: e.target.value })} />
            </div>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs rounded-md bg-muted hover:bg-muted/70">Cancel</button>
              <button type="submit" disabled={creating || !form.name} className="px-3 py-1.5 text-xs rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2">
                {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null} Create
              </button>
            </div>
          </motion.form>
        )}

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md shadow-card overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading patients…
            </div>
          ) : patients.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">No patients yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/40">
                <tr className="text-left text-[10px] uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-2">Name</th>
                  <th className="px-4 py-2">MRN</th>
                  <th className="px-4 py-2">Sex</th>
                  <th className="px-4 py-2">DOB</th>
                  <th className="px-4 py-2">GA wk</th>
                  <th className="px-4 py-2">Care plan</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {patients.map((p) => (
                  <tr key={p.id} className={`border-t border-border/40 hover:bg-muted/30 ${p.id === patientId ? "bg-primary/5" : ""}`}>
                    <td className="px-4 py-2"><Link href={`/patients/${p.id}`} className="font-medium hover:underline">{p.name}</Link></td>
                    <td className="px-4 py-2 text-muted-foreground font-mono text-xs">{p.mrn || "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{p.sex || "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{p.dob || "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{p.gestational_age_weeks ?? "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground text-xs">{p.assigned_clinician_id || "—"}</td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => setPatientId(p.id === patientId ? null : p.id)}
                        className={`text-xs px-2 py-1 rounded-md ${p.id === patientId ? "bg-primary/20 text-primary" : "bg-muted hover:bg-muted/70"}`}
                      >
                        {p.id === patientId ? "Active" : "Set active"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
