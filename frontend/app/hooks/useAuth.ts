"use client";

import { useCallback, useEffect, useState } from "react";
import { clearToken, getMe, type AuthMe } from "../lib/api";

export function useAuth() {
  const [me, setMe] = useState<AuthMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((r) => !cancelled && setMe(r))
      .catch(() => !cancelled && setMe(null))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  const logout = useCallback(() => {
    clearToken();
    if (typeof window !== "undefined") {
      // Also clear the cookie mirror used by middleware
      document.cookie = "medverse_token=; Path=/; Max-Age=0";
      window.location.href = "/login";
    }
  }, []);

  return { me, loading, logout };
}
