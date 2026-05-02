"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X } from "lucide-react";
import { fetchAlerts, type Alert } from "../lib/api";
import { useActivePatient } from "../hooks/useActivePatient";

const POLL_MS = 5_000;

export function AlertBanner() {
  const { patientId } = useActivePatient();
  const [criticals, setCriticals] = useState<Alert[]>([]);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastSeenIdRef = useRef<number>(0);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await fetchAlerts({ patient_id: patientId || undefined, unacknowledged: true, limit: 20 });
        if (cancelled) return;
        const c = r.filter((a) => a.severity >= 8 && !dismissed.has(a.id));
        const newest = c[0]?.id || 0;
        if (newest > lastSeenIdRef.current) {
          lastSeenIdRef.current = newest;
          if (audioRef.current) {
            audioRef.current.currentTime = 0;
            audioRef.current.play().catch(() => {});
          }
          if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted") {
            try { new Notification("MedVerse — critical alert", { body: c[0]?.message }); } catch { /* noop */ }
          }
        }
        setCriticals(c);
      } catch { /* offline */ }
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [patientId, dismissed]);

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  if (criticals.length === 0) return null;

  return (
    <>
      {/* Short alarm chirp — single beep so it isn't disruptive in a demo */}
      <audio ref={audioRef} preload="auto" src="data:audio/wav;base64,UklGRmQDAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YUADAAAA" />
      <div className="fixed top-2 left-1/2 -translate-x-1/2 z-50 w-[min(96vw,640px)] space-y-2">
        <AnimatePresence>
          {criticals.slice(0, 3).map((a) => (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, y: -16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              className="rounded-lg border border-rose-500/50 bg-rose-950/95 backdrop-blur-md text-rose-50 p-3 shadow-2xl flex items-start gap-3"
            >
              <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 animate-pulse" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider opacity-90">
                  <span className="px-1.5 py-0.5 bg-rose-500/30 rounded-sm font-semibold">Critical · {a.severity}/10</span>
                  <span className="font-mono opacity-70">{a.source}</span>
                </div>
                <p className="mt-0.5 text-sm font-medium">{a.message}</p>
                <Link href="/alerts" className="text-[11px] underline opacity-80 hover:opacity-100">
                  Open alert center →
                </Link>
              </div>
              <button
                onClick={() => setDismissed((s) => new Set(s).add(a.id))}
                aria-label="Dismiss"
                className="text-rose-200/70 hover:text-rose-100 flex-shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </>
  );
}
