"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "../lib/api";
import { ShieldCheck, Loader2 } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("medverse");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      router.replace("/");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-5 bg-card border border-border rounded-xl p-8 shadow-sm"
      >
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-primary" />
          <h1 className="font-display text-lg font-semibold tracking-tight">
            MedVerse sign-in
          </h1>
        </div>
        <p className="text-xs text-muted-foreground -mt-3">
          Dev credentials default to <code>medverse / medverse</code>. Change
          <code> MEDVERSE_DEV_USERNAME</code> and <code>MEDVERSE_DEV_PASSWORD</code> in
          the backend <code>.env</code> for anything real.
        </p>

        <label className="block space-y-1">
          <span className="text-sm text-foreground">Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm text-foreground">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>

        {error && (
          <div className="text-sm text-red-500 bg-red-500/10 rounded px-2 py-1">{error}</div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-md bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-60"
        >
          {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
          Sign in
        </button>

        <p className="text-[11px] text-muted-foreground">
          Auth is opt-in at the backend (<code>MEDVERSE_AUTH_ENABLED=true</code>). With auth
          off, any credentials return a token and the dashboard works as before.
        </p>
      </form>
    </div>
  );
}
