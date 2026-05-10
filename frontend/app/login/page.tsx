"use client";

import { useRouter } from "next/navigation";
import { Shield, Stethoscope, User, ArrowRight } from "lucide-react";
import { setToken } from "../lib/api";

export default function LoginPage() {
  const router = useRouter();

  function signInAs(role: "doctor" | "patient") {
    setToken(`mock-${role}-token`);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("medverse_role", role);
      // Mirror the role into the cookie the middleware checks for role-based routing
      document.cookie = `aegis_role=${role}; Path=/; Max-Age=${60 * 60 * 8}; SameSite=Lax`;
    }
    router.replace(role === "patient" ? "/dashboard/patient" : "/dashboard/doctor");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6 relative overflow-hidden">

      {/* Background orbs */}
      <div className="absolute w-[500px] h-[500px] rounded-full blur-3xl bg-primary/5 -top-40 -left-40 pointer-events-none" />
      <div className="absolute w-[400px] h-[400px] rounded-full blur-3xl bg-accent/5 -bottom-20 -right-20 pointer-events-none" />

      <div className="relative w-full max-w-md">
        <div className="absolute -inset-px rounded-2xl bg-gradient-to-br from-primary/30 via-transparent to-accent/20 pointer-events-none" />

        <div className="relative bg-card border border-border rounded-2xl p-8 shadow-card space-y-6">
          {/* Logo */}
          <div className="flex flex-col items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center shadow-glow">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <div className="text-center">
              <h1 className="font-display text-xl font-bold tracking-tight text-foreground">
                Welcome to MedVerse
              </h1>
              <p className="text-xs text-muted-foreground mt-1">
                Demo mode — pick a role to enter the dashboard
              </p>
            </div>
          </div>

          {/* Role buttons */}
          <div className="grid gap-3">
            <button
              type="button"
              onClick={() => signInAs("doctor")}
              className="group flex items-center justify-between gap-3 p-4 rounded-xl border border-border bg-background/60 hover:border-primary hover:bg-primary/5 transition-all hover:scale-[1.01] active:scale-[0.99]"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <Stethoscope className="w-5 h-5 text-primary" />
                </div>
                <div className="text-left">
                  <div className="text-sm font-semibold text-foreground">Sign in as Doctor</div>
                  <div className="text-xs text-muted-foreground">Clinical dashboard, multi-patient view</div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </button>

            <button
              type="button"
              onClick={() => signInAs("patient")}
              className="group flex items-center justify-between gap-3 p-4 rounded-xl border border-border bg-background/60 hover:border-accent hover:bg-accent/5 transition-all hover:scale-[1.01] active:scale-[0.99]"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/30 flex items-center justify-center">
                  <User className="w-5 h-5 text-accent" />
                </div>
                <div className="text-left">
                  <div className="text-sm font-semibold text-foreground">Sign in as Patient</div>
                  <div className="text-xs text-muted-foreground">Personal vitals, vest stream, history</div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-accent transition-colors" />
            </button>
          </div>

          <p className="text-center text-[11px] text-muted-foreground/70 pt-2 border-t border-border/50">
            Authentication is disabled in demo mode. No credentials required.
          </p>
        </div>
      </div>
    </div>
  );
}
