"use client";

import { useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Download, FileJson, Loader2, ExternalLink } from "lucide-react";
import { useActivePatient } from "../hooks/useActivePatient";
import { fetchFhir, FHIR_RESOURCES } from "../lib/api";

const SPECIALTY_DIAG_REPORTS = [
  "Cardiology",
  "Pulmonary",
  "Neurology",
  "Dermatology",
  "Obstetrics",
  "Ocular",
  "General Physician",
];

function downloadJson(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function FhirExportPage() {
  const { patientId } = useActivePatient();
  const [busy, setBusy] = useState<string | null>(null);
  const [previews, setPreviews] = useState<Record<string, unknown>>({});
  const [err, setErr] = useState<string | null>(null);

  const fetchOne = async (key: string, path: string) => {
    setBusy(key);
    setErr(null);
    try {
      const data = await fetchFhir(path, patientId || undefined);
      setPreviews((p) => ({ ...p, [key]: data }));
      const safeName = path.replace(/[/{}]/g, "_") + ".json";
      downloadJson(safeName, data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6 max-w-5xl">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">FHIR R4 export</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Pull telemetry + interpretations as LOINC-coded FHIR resources for hospital EMRs.
            Patient context: <code className="px-1 bg-muted rounded">{patientId || "default"}</code>.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Top-level resources</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {FHIR_RESOURCES.map((r) => (
              <div key={r.key} className="flex items-center gap-3 p-3 rounded-md bg-muted/30 border border-border/50">
                <FileJson className="w-5 h-5 text-primary flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{r.label}</div>
                  <code className="text-[10px] text-muted-foreground truncate block">{r.path}</code>
                </div>
                <button
                  onClick={() => fetchOne(r.key, r.path)}
                  disabled={busy === r.key}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary/10 hover:bg-primary/20 text-primary text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  {busy === r.key ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                  {busy === r.key ? "Fetching" : "Fetch & download"}
                </button>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-card border border-border rounded-md p-4 shadow-card">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">DiagnosticReport per specialty</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {SPECIALTY_DIAG_REPORTS.map((s) => {
              const slug = s.toLowerCase().replace(/\s+/g, "-");
              const path = `/api/fhir/DiagnosticReport/${slug}/latest`;
              return (
                <button
                  key={s}
                  onClick={() => fetchOne(`diag-${slug}`, path)}
                  disabled={busy === `diag-${slug}`}
                  className="flex items-center justify-between gap-2 px-3 py-2 rounded-md bg-muted/30 hover:bg-muted/60 border border-border/50 text-xs font-medium transition-colors disabled:opacity-50"
                >
                  <span>{s}</span>
                  {busy === `diag-${slug}` ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5 text-muted-foreground" />}
                </button>
              );
            })}
          </div>
        </motion.div>

        {err && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-md p-3 text-xs text-rose-300">
            <strong>Error:</strong> {err}
          </div>
        )}

        {Object.keys(previews).length > 0 && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-md p-4 shadow-card">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex-1">Last preview</h3>
              <a
                href="https://www.hl7.org/fhir/R4/"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-primary flex items-center gap-1 hover:underline"
              >
                FHIR R4 spec <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <pre className="text-[10px] bg-muted/30 rounded p-3 overflow-x-auto max-h-64 font-mono">
              {JSON.stringify(Object.values(previews).slice(-1)[0], null, 2)}
            </pre>
          </motion.div>
        )}
      </div>
    </DashboardLayout>
  );
}
