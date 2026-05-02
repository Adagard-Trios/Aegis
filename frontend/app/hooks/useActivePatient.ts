"use client";

import { useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "medverse_active_patient";

export function useActivePatient() {
  const [patientId, setPatientIdState] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      setPatientIdState(window.localStorage.getItem(STORAGE_KEY));
    } catch {
      /* noop */
    }
  }, []);

  const setPatientId = useCallback((id: string | null) => {
    setPatientIdState(id);
    if (typeof window === "undefined") return;
    try {
      if (id) window.localStorage.setItem(STORAGE_KEY, id);
      else window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* noop */
    }
  }, []);

  return { patientId, setPatientId };
}
