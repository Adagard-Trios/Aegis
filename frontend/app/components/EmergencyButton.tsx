"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Siren, X, Loader2 } from "lucide-react";
import { postEmergency } from "../lib/api";
import { useActivePatient } from "../hooks/useActivePatient";
import { useVestStream } from "../hooks/useVestStream";

export function EmergencyButton() {
  const { patientId } = useActivePatient();
  const { data } = useVestStream();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<string | null>(null);

  const trigger = async () => {
    setBusy(true);
    setResult(null);
    let geo: { lat: number; lon: number } | undefined;
    try {
      if (typeof navigator !== "undefined" && navigator.geolocation) {
        geo = await new Promise<{ lat: number; lon: number } | undefined>((resolve) => {
          navigator.geolocation.getCurrentPosition(
            (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
            () => resolve(undefined),
            { timeout: 1500 }
          );
        });
      }
    } catch { /* ignore */ }
    try {
      const r = await postEmergency({
        patient_id: patientId || undefined,
        message: message || "Manual emergency activation",
        vitals: (data?.vitals as Record<string, unknown>) || {},
        geolocation: geo,
      });
      setResult(r.webhook ? `Webhook fired: ${r.webhook}` : "Critical alert recorded.");
    } catch (e) {
      setResult(`Failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Emergency"
        title="Emergency action"
        className="fixed bottom-24 right-6 w-14 h-14 rounded-full bg-rose-600 hover:bg-rose-500 text-white shadow-2xl flex items-center justify-center z-40 transition-transform hover:scale-105"
      >
        <Siren className="w-6 h-6" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
            onClick={() => !busy && setOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.95, y: 8 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 8 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-xl bg-rose-950 border-2 border-rose-500/60 p-5 text-rose-50 shadow-2xl"
            >
              <div className="flex items-center gap-3 mb-3">
                <Siren className="w-6 h-6 animate-pulse" />
                <h2 className="text-lg font-bold flex-1">Emergency action</h2>
                <button onClick={() => setOpen(false)} disabled={busy} className="text-rose-200/70 hover:text-rose-100 disabled:opacity-50">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm mb-3 text-rose-100/80">
                Will record a critical alert + snapshot current vitals + (if granted) browser geolocation.
                If <code className="bg-rose-900/60 px-1 rounded">MEDVERSE_EMERGENCY_WEBHOOK</code> is set
                on the backend, it will POST to that URL.
              </p>
              <textarea
                placeholder="Optional context (e.g., 'patient unresponsive, no pulse')"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={3}
                className="w-full bg-rose-950/60 border border-rose-500/40 rounded px-3 py-2 text-sm placeholder:text-rose-300/50"
              />
              <div className="mt-3 flex gap-2 justify-end">
                <button onClick={() => setOpen(false)} disabled={busy} className="px-3 py-2 rounded-md bg-rose-900/40 hover:bg-rose-900/60 text-sm">
                  Cancel
                </button>
                <button
                  onClick={trigger}
                  disabled={busy}
                  className="px-4 py-2 rounded-md bg-rose-500 hover:bg-rose-400 text-white text-sm font-bold flex items-center gap-2 disabled:opacity-50"
                >
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Siren className="w-4 h-4" />}
                  Trigger emergency
                </button>
              </div>
              {result && <p className="mt-3 text-xs text-rose-100/90 italic">{result}</p>}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
