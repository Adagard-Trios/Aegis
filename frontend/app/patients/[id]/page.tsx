"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import DashboardLayout from "../../components/DashboardLayout";
import { motion } from "framer-motion";
import { ChevronLeft, Activity, Heart, BarChart3, Wind, Brain, Baby, ClipboardList, Loader2 } from "lucide-react";
import { getPatient, listCarePlans, assignCarePlan, type Patient, type CarePlan } from "../../lib/api";

export default function PatientDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const [patient, setPatient] = useState<Patient | null>(null);
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingPlan, setSavingPlan] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        if (!id) return;
        const [p, pl] = await Promise.all([getPatient(id), listCarePlans()]);
        if (!cancelled) {
          setPatient(p);
          setPlans(pl);
        }
      } catch { /* ignore */ }
      finally { if (!cancelled) setLoading(false); }
    };
    load();
    return () => { cancelled = true; };
  }, [id]);

  const choosePlan = async (planId: string) => {
    if (!id) return;
    setSavingPlan(true);
    try {
      await assignCarePlan(id, planId);
      setPatient((p) => p ? { ...p, assigned_clinician_id: p.assigned_clinician_id } as Patient : p);
      const updated = await getPatient(id);
      setPatient(updated);
    } finally {
      setSavingPlan(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="p-8 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading…
        </div>
      </DashboardLayout>
    );
  }

  if (!patient) {
    return (
      <DashboardLayout>
        <div className="p-8 text-sm text-muted-foreground">Patient not found.</div>
      </DashboardLayout>
    );
  }

  const currentPlan = plans.find((p) => p.id === (patient as Patient & { care_plan_id?: string }).care_plan_id);

  const links = [
    { href: `/?patient_id=${patient.id}`, label: "Dashboard", icon: BarChart3 },
    { href: `/digital-twin?patient_id=${patient.id}`, label: "Digital Twin", icon: Activity },
    { href: `/cardiology?patient_id=${patient.id}`, label: "Cardiology", icon: Heart },
    { href: `/respiratory?patient_id=${patient.id}`, label: "Respiratory", icon: Wind },
    { href: `/neurology?patient_id=${patient.id}`, label: "Neurology", icon: Brain },
    { href: `/obstetrics?patient_id=${patient.id}`, label: "Obstetrics", icon: Baby },
    { href: `/diagnostics?patient_id=${patient.id}`, label: "Diagnostics", icon: ClipboardList },
    { href: `/history?patient_id=${patient.id}`, label: "History", icon: BarChart3 },
  ];

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6 max-w-5xl">
        <Link href="/patients" className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
          <ChevronLeft className="w-3.5 h-3.5" /> Back to patients
        </Link>

        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">{patient.name}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            MRN <code className="px-1 bg-muted rounded">{patient.mrn || "—"}</code> ·
            {patient.sex || "—"} · DOB {patient.dob || "—"}
            {patient.gestational_age_weeks ? ` · ${patient.gestational_age_weeks} wk GA` : ""}
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Care plan</h3>
          {currentPlan ? (
            <div className="text-sm mb-3">
              <span className="font-semibold">{currentPlan.name}</span>
              <span className="text-muted-foreground"> — monitoring every {currentPlan.monitoring_frequency_s}s</span>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground mb-3">No care plan assigned. Default thresholds apply.</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {plans.map((p) => (
              <button
                key={p.id}
                onClick={() => choosePlan(p.id)}
                disabled={savingPlan}
                className={`p-3 rounded-md border text-left transition-colors ${
                  (patient as Patient & { care_plan_id?: string }).care_plan_id === p.id
                    ? "border-primary/60 bg-primary/10"
                    : "border-border hover:bg-muted/30"
                }`}
              >
                <div className="text-sm font-semibold">{p.name}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">
                  {Object.entries(p.thresholds).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ")}
                </div>
              </button>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Open in patient context</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {links.map(({ href, label, icon: Icon }) => (
              <Link key={label} href={href} className="flex items-center gap-2 p-3 rounded-md bg-muted/30 hover:bg-muted/60 border border-border/50 text-sm font-medium">
                <Icon className="w-4 h-4 text-primary" /> {label}
              </Link>
            ))}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
