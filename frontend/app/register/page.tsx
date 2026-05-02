"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Shield, Loader2, Eye, EyeOff, ArrowRight, Stethoscope, User } from "lucide-react";

type Role = "doctor" | "patient";

export default function RegisterPage() {
  const router = useRouter();
  const [role, setRole] = useState<Role>("doctor");
  const [form, setForm] = useState({
    name: "", username: "", email: "", password: "", confirm: "",
    specialty: "", dob: "", sex: "",
  });
  const [showPw, setShowPw] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError("Passwords do not match");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          username: form.username,
          email: form.email,
          password: form.password,
          role,
          specialty: role === "doctor" ? form.specialty : undefined,
          dob: role === "patient" ? form.dob : undefined,
          sex: role === "patient" ? form.sex : undefined,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error((data as { detail?: string }).detail ?? `Error ${res.status}`);
      }
      router.push("/login?registered=1");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6 relative overflow-hidden">

      {/* Orbs */}
      <div className="absolute w-[500px] h-[500px] rounded-full blur-3xl bg-primary/5 -top-40 -right-40 pointer-events-none" />
      <div className="absolute w-[400px] h-[400px] rounded-full blur-3xl bg-accent/5 -bottom-20 -left-20 pointer-events-none" />

      <div className="relative w-full max-w-md">
        <div className="absolute -inset-px rounded-2xl bg-gradient-to-br from-primary/30 via-transparent to-accent/20 pointer-events-none" />

        <form
          onSubmit={onSubmit}
          className="relative bg-card border border-border rounded-2xl p-8 shadow-card space-y-5"
        >
          {/* Logo */}
          <div className="flex flex-col items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center shadow-glow">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <div className="text-center">
              <h1 className="font-display text-xl font-bold tracking-tight text-foreground">
                Create your account
              </h1>
              <p className="text-xs text-muted-foreground mt-1">
                Join Aegis — Clinical Intelligence Platform
              </p>
            </div>
          </div>

          {/* Role selector */}
          <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-muted/50 border border-border">
            {(["doctor", "patient"] as Role[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  role === r
                    ? "bg-primary text-primary-foreground shadow-glow"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {r === "doctor" ? <Stethoscope className="w-4 h-4" /> : <User className="w-4 h-4" />}
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>

          {/* Common fields */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5 col-span-2">
              <label className="text-xs font-medium text-foreground">Full name</label>
              <input
                required
                placeholder="Dr. Jane Smith"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all placeholder:text-muted-foreground/50"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Username</label>
              <input
                required
                placeholder="janesmithmd"
                value={form.username}
                onChange={(e) => set("username", e.target.value)}
                className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all placeholder:text-muted-foreground/50"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Email</label>
              <input
                type="email"
                required
                placeholder="jane@hospital.org"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all placeholder:text-muted-foreground/50"
              />
            </div>
          </div>

          {/* Role-specific fields */}
          {role === "doctor" ? (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Specialty</label>
              <select
                value={form.specialty}
                onChange={(e) => set("specialty", e.target.value)}
                className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary transition-all text-foreground"
              >
                <option value="">Select specialty…</option>
                {["Cardiology", "Pulmonology", "Neurology", "Obstetrics", "Dermatology", "General Physician", "Oculometry"].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Date of birth</label>
                <input
                  type="date"
                  value={form.dob}
                  onChange={(e) => set("dob", e.target.value)}
                  className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary transition-all text-foreground"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Sex</label>
                <select
                  value={form.sex}
                  onChange={(e) => set("sex", e.target.value)}
                  className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary transition-all text-foreground"
                >
                  <option value="">Select…</option>
                  <option value="F">Female</option>
                  <option value="M">Male</option>
                  <option value="X">Non-binary / other</option>
                </select>
              </div>
            </div>
          )}

          {/* Password */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Password</label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  required
                  minLength={8}
                  placeholder="Min 8 characters"
                  value={form.password}
                  onChange={(e) => set("password", e.target.value)}
                  className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 pr-9 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all placeholder:text-muted-foreground/50"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Confirm</label>
              <input
                type="password"
                required
                placeholder="Repeat password"
                value={form.confirm}
                onChange={(e) => set("confirm", e.target.value)}
                className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all placeholder:text-muted-foreground/50"
              />
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 disabled:opacity-60 shadow-glow transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
            {submitting ? "Creating account…" : "Create account"}
          </button>

          <p className="text-center text-xs text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
