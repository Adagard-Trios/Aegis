"use client";

/**
 * Twin-timeline hook for the /digital-twin time slider.
 *
 * Pulls historical twin states from /api/digital-twin/timeline at a
 * configurable refresh interval. Sized for the time-slider use case:
 * fetches the last `windowMinutes` of history and refreshes every
 * `refreshSeconds`. Returns the raw state list (oldest-first) plus
 * loading + error flags, so the consumer can drive a slider widget
 * directly off `states[index].state`.
 *
 * Why a hook (and not just a useEffect): we want one consistent
 * timeline-fetcher that frontend pages can drop in without each
 * re-implementing the URL params + retry policy. Mirrors useVestStream's
 * shape so the two are interchangeable in muscle memory.
 */
import { useEffect, useRef, useState } from "react";
import {
  fetchTwinTimeline,
  type TwinName,
  type TwinTimelineResponse,
} from "../lib/api";

interface UseTwinTimelineOpts {
  twin: TwinName;
  patientId?: string | null;
  windowMinutes?: number;     // default 60 — how far back to fetch
  limit?: number;             // default 360 — max points returned
  refreshSeconds?: number;    // default 10 — poll interval
  enabled?: boolean;          // default true — pause when false
}

interface UseTwinTimelineResult {
  states: TwinTimelineResponse["states"];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTwinTimeline({
  twin,
  patientId,
  windowMinutes = 60,
  limit = 360,
  refreshSeconds = 10,
  enabled = true,
}: UseTwinTimelineOpts): UseTwinTimelineResult {
  const [states, setStates] = useState<TwinTimelineResponse["states"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(false);

  const refresh = async () => {
    if (!enabled) return;
    try {
      setError(null);
      const now = Date.now() / 1000;
      const r = await fetchTwinTimeline(twin, {
        patient_id: patientId || undefined,
        from_ts: now - windowMinutes * 60,
        to_ts: now,
        limit,
      });
      if (!cancelRef.current) {
        setStates(r.states || []);
        if (r.error) setError(r.error);
      }
    } catch (e) {
      if (!cancelRef.current) {
        setError(e instanceof Error ? e.message : "timeline fetch failed");
      }
    } finally {
      if (!cancelRef.current) setLoading(false);
    }
  };

  useEffect(() => {
    cancelRef.current = false;
    setLoading(true);
    refresh();
    if (!enabled) return () => { cancelRef.current = true; };
    const id = setInterval(refresh, refreshSeconds * 1000);
    return () => {
      cancelRef.current = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [twin, patientId, windowMinutes, limit, refreshSeconds, enabled]);

  return { states, loading, error, refresh };
}
