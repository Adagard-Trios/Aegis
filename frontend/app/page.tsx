"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Shield, Heart, Brain, Wind, Baby, Zap, Activity,
  ArrowRight, ChevronRight, Cpu, Wifi, Lock, BarChart3,
  Users, Bell, FileJson, Stethoscope, Star, Github,
} from "lucide-react";

// ── Animated ECG line ─────────────────────────────────────────────
function ECGLine() {
  const path = "M0,50 L40,50 L50,50 L55,10 L60,90 L65,30 L70,50 L80,50 L120,50 L125,50 L130,15 L135,85 L140,35 L145,50 L155,50 L200,50";
  return (
    <svg
      viewBox="0 0 200 100"
      className="w-full h-full"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="ecg-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="hsl(191 100% 50% / 0)" />
          <stop offset="30%" stopColor="hsl(191 100% 50% / 0.8)" />
          <stop offset="70%" stopColor="hsl(191 100% 50% / 0.8)" />
          <stop offset="100%" stopColor="hsl(191 100% 50% / 0)" />
        </linearGradient>
        <filter id="ecg-glow">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        d={path}
        fill="none"
        stroke="url(#ecg-grad)"
        strokeWidth="1.5"
        filter="url(#ecg-glow)"
        className="animate-ecg-draw"
      />
    </svg>
  );
}

// ── Floating orb ─────────────────────────────────────────────────
function Orb({ className }: { className: string }) {
  return <div className={`absolute rounded-full blur-3xl pointer-events-none ${className}`} />;
}

// ── Stat card ────────────────────────────────────────────────────
function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1 px-6 py-4 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm">
      <span className="font-display text-2xl md:text-3xl font-bold text-primary">{value}</span>
      <span className="text-xs text-muted-foreground text-center">{label}</span>
    </div>
  );
}

// ── Feature card ─────────────────────────────────────────────────
function FeatureCard({
  icon: Icon,
  title,
  desc,
  delay,
}: {
  icon: React.ElementType;
  title: string;
  desc: string;
  delay: string;
}) {
  return (
    <div
      className="group relative p-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm hover:border-primary/40 hover:bg-primary/5 transition-all duration-300"
      style={{ animationDelay: delay }}
    >
      <div className="w-11 h-11 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4 group-hover:bg-primary/20 group-hover:scale-110 transition-all duration-300">
        <Icon className="w-5 h-5 text-primary" />
      </div>
      <h3 className="font-display font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

// ── Step card ────────────────────────────────────────────────────
function StepCard({
  num,
  title,
  desc,
}: {
  num: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="flex gap-5 items-start">
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center">
        <span className="font-display font-bold text-primary text-sm">{num}</span>
      </div>
      <div>
        <h4 className="font-display font-semibold text-foreground mb-1">{title}</h4>
        <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

// ── Specialty pill ────────────────────────────────────────────────
function Pill({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/10 bg-white/5 text-xs text-muted-foreground hover:border-primary/40 hover:text-primary transition-all duration-200">
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

// ── Main landing page ─────────────────────────────────────────────
export default function LandingPage() {
  const router = useRouter();
  const [scrollY, setScrollY] = useState(0);
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const parallaxY = scrollY * 0.3;

  return (
    <div className="min-h-screen bg-background overflow-x-hidden">

      {/* ── Navbar ── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-12 h-16 border-b border-white/5 bg-background/80 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-glow">
            <Shield className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-display font-bold text-lg tracking-wide text-foreground">AEGIS</span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#how" className="hover:text-foreground transition-colors">How it works</a>
          <a href="#specialties" className="hover:text-foreground transition-colors">Specialties</a>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5">
            Sign in
          </Link>
          <Link
            href="/register"
            className="text-sm font-semibold px-4 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-glow"
          >
            Get started
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section ref={heroRef} className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-16 overflow-hidden">

        {/* Background orbs */}
        <Orb className="w-[600px] h-[600px] bg-primary/8 top-[-100px] left-[-200px]" />
        <Orb className="w-[500px] h-[500px] bg-accent/6 bottom-[-50px] right-[-150px]" />
        <Orb className="w-[300px] h-[300px] bg-primary/5 top-[40%] right-[20%]" />

        {/* Grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: "linear-gradient(hsl(191 100% 50%) 1px, transparent 1px), linear-gradient(90deg, hsl(191 100% 50%) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
            transform: `translateY(${parallaxY}px)`,
          }}
        />

        {/* ECG strip */}
        <div className="absolute bottom-0 left-0 right-0 h-16 opacity-20 pointer-events-none">
          <ECGLine />
        </div>

        {/* Badge */}
        <div className="relative z-10 mb-6 inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/5 backdrop-blur-sm text-xs text-primary font-semibold tracking-wide">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
          Context-Aware Multi-Agent Clinical Intelligence
        </div>

        {/* Headline */}
        <h1 className="relative z-10 font-display text-center text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] max-w-4xl">
          <span className="text-foreground">Clinical telemetry,</span>
          <br />
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage: "linear-gradient(135deg, hsl(191 100% 50%), hsl(160 84% 39%), hsl(191 100% 65%))",
            }}
          >
            reimagined.
          </span>
        </h1>

        <p className="relative z-10 mt-6 text-center text-lg md:text-xl text-muted-foreground max-w-2xl leading-relaxed">
          Stream live biometrics from a wearable vest, interpret them with a swarm of AI specialty agents, and surface real-time insights — in milliseconds, not hours.
        </p>

        {/* CTAs */}
        <div className="relative z-10 mt-10 flex flex-col sm:flex-row items-center gap-4">
          <button
            onClick={() => router.push("/register")}
            className="group flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow-strong transition-all duration-200 hover:scale-105"
          >
            Start for free
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
          <button
            onClick={() => router.push("/login")}
            className="flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold border border-white/10 bg-white/5 backdrop-blur-sm text-foreground hover:border-primary/40 hover:bg-primary/5 transition-all duration-200"
          >
            Sign in
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Stats row */}
        <div className="relative z-10 mt-16 grid grid-cols-2 md:grid-cols-4 gap-3 w-full max-w-3xl">
          <StatCard value="9" label="AI Expert Agents" />
          <StatCard value="30+" label="Sensor Channels" />
          <StatCard value="10 Hz" label="Telemetry Rate" />
          <StatCard value="FHIR R4" label="Interoperable" />
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="relative px-6 md:px-12 py-28 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <span className="text-xs font-semibold uppercase tracking-widest text-primary mb-3 block">Platform features</span>
          <h2 className="font-display text-4xl md:text-5xl font-bold text-foreground mb-4">
            Everything you need.
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            From raw sensor signals to AI-generated clinical assessments — the entire pipeline in one platform.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <FeatureCard
            icon={Activity}
            title="Live Telemetry Stream"
            desc="10 Hz SSE stream from 30+ sensor channels — PPG, ECG, IMU, temperature, fetal, and acoustic — with < 100 ms end-to-end latency."
            delay="0ms"
          />
          <FeatureCard
            icon={Brain}
            title="Multi-Agent AI"
            desc="A LangGraph swarm of 9 specialty experts — cardiology, neurology, pulmonary, obstetrics and more — running in parallel, synthesised by a general physician."
            delay="60ms"
          />
          <FeatureCard
            icon={Cpu}
            title="3D Digital Twin"
            desc="A React Three Fiber anatomical model reacting in real time to heart rate, posture, temperature, contractions, and fetal kicks."
            delay="120ms"
          />
          <FeatureCard
            icon={BarChart3}
            title="PK/PD Drug Simulation"
            desc="Two-compartment Bateman pharmacokinetic curves for labetalol and oxytocin, with CYP2D6 metabolizer-aware clearance and live effect charts."
            delay="180ms"
          />
          <FeatureCard
            icon={FileJson}
            title="FHIR R4 Interoperability"
            desc="Every telemetry snapshot and diagnostic report serialised as LOINC-coded Observation, Bundle, and DiagnosticReport resources — drop-in EMR compatible."
            delay="240ms"
          />
          <FeatureCard
            icon={Lock}
            title="Secure by Default"
            desc="JWT bearer auth, env-driven CORS allowlist, ECG biometric passive identity, and federated learning so raw biometrics never leave the device."
            delay="300ms"
          />
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how" className="relative px-6 md:px-12 py-24">
        <Orb className="w-[500px] h-[500px] bg-primary/6 top-0 right-[-100px]" />
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-xs font-semibold uppercase tracking-widest text-primary mb-3 block">Workflow</span>
            <h2 className="font-display text-4xl md:text-5xl font-bold text-foreground mb-4">How it works</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Hardware-to-insight in three steps. No configuration. No compromise.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-16 items-center">
            {/* Steps */}
            <div className="space-y-10">
              <StepCard
                num="01"
                title="Wear the Aegis Vest"
                desc="The ESP32-S3 vest streams 30+ biometric channels over BLE at 40 Hz. No hardware? The mock generator keeps every part of the stack running."
              />
              <StepCard
                num="02"
                title="Stream to the Backend"
                desc="FastAPI buffers signals, runs scipy DSP to derive HR, HRV, SpO₂, breathing rate, IMU biomarkers, and fetal CTG — then pushes at 10 Hz over SSE."
              />
              <StepCard
                num="03"
                title="AI Interprets & Alerts"
                desc="The LangGraph agent swarm fires in parallel, each expert grounded in clinical knowledge and RAG memory. Critical findings trigger real-time alerts."
              />
            </div>

            {/* Visual panel */}
            <div className="relative rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-6 overflow-hidden">
              <Orb className="w-48 h-48 bg-primary/10 -top-10 -right-10" />
              {/* Mock dashboard preview */}
              <div className="space-y-3 relative z-10">
                {/* Header row */}
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-2 h-2 rounded-full bg-vital-green animate-pulse" />
                  <span className="text-xs text-muted-foreground font-mono">VEST STREAMING · 40 Hz</span>
                </div>
                {/* Vital tiles */}
                {[
                  { label: "Heart Rate", value: "78", unit: "bpm", color: "text-red-400" },
                  { label: "SpO₂", value: "98", unit: "%", color: "text-primary" },
                  { label: "Breathing Rate", value: "14", unit: "/min", color: "text-accent" },
                  { label: "HRV RMSSD", value: "42", unit: "ms", color: "text-yellow-400" },
                ].map((v) => (
                  <div key={v.label} className="flex items-center justify-between px-4 py-2.5 rounded-lg bg-white/5 border border-white/5">
                    <span className="text-xs text-muted-foreground">{v.label}</span>
                    <span className={`font-display font-bold text-sm ${v.color}`}>
                      {v.value} <span className="text-xs font-normal text-muted-foreground">{v.unit}</span>
                    </span>
                  </div>
                ))}
                {/* Agent output */}
                <div className="mt-4 px-4 py-3 rounded-lg bg-primary/5 border border-primary/20">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Stethoscope className="w-3 h-3 text-primary" />
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-primary">AI Agent · Cardiology</span>
                    <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-vital-green/15 text-vital-green font-semibold">NORMAL</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Sinus rhythm with normal rate. HRV within physiological range. No arrhythmia indicators detected.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Specialties ── */}
      <section id="specialties" className="relative px-6 md:px-12 py-24 max-w-5xl mx-auto text-center">
        <span className="text-xs font-semibold uppercase tracking-widest text-primary mb-3 block">AI Agents</span>
        <h2 className="font-display text-4xl md:text-5xl font-bold text-foreground mb-4">
          Seven specialty experts.
          <br />
          <span className="text-muted-foreground text-3xl font-normal">One unified diagnosis.</span>
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto mb-12">
          Each expert agent is grounded in a clinical knowledge base and a Chroma-backed RAG memory, emitting structured JSON assessments with confidence scores.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Pill icon={Heart} label="Cardiology" />
          <Pill icon={Wind} label="Pulmonary" />
          <Pill icon={Brain} label="Neurology" />
          <Pill icon={Baby} label="Obstetrics" />
          <Pill icon={Activity} label="Dermatology" />
          <Pill icon={Zap} label="Ocular" />
          <Pill icon={Stethoscope} label="General Physician" />
        </div>

        {/* CTA banner */}
        <div className="mt-20 relative rounded-2xl border border-primary/20 bg-primary/5 p-10 overflow-hidden">
          <Orb className="w-64 h-64 bg-primary/10 top-[-60px] left-[-60px]" />
          <Orb className="w-64 h-64 bg-accent/8 bottom-[-40px] right-[-40px]" />
          <div className="relative z-10">
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-3">
              Ready to go live?
            </h2>
            <p className="text-muted-foreground mb-8 max-w-md mx-auto">
              Sign up in seconds — no hardware required. The mock generator gives you full access to every feature.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={() => router.push("/register")}
                className="group flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow-strong transition-all duration-200 hover:scale-105"
              >
                Create account
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
              <button
                onClick={() => router.push("/login")}
                className="flex items-center gap-2 px-8 py-3.5 rounded-xl font-semibold border border-white/10 text-foreground hover:border-primary/40 transition-all duration-200"
              >
                Sign in
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-white/5 px-6 md:px-12 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-primary" />
          <span className="font-display font-semibold text-foreground">AEGIS</span>
          <span>· Context-Aware Clinical Intelligence Platform</span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/login" className="hover:text-foreground transition-colors">Login</Link>
          <Link href="/register" className="hover:text-foreground transition-colors">Register</Link>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="hover:text-foreground transition-colors flex items-center gap-1"
          >
            <Github className="w-3.5 h-3.5" />
            GitHub
          </a>
          <div className="flex items-center gap-1.5">
            <Star className="w-3 h-3 text-primary" />
            <span>MIT License</span>
          </div>
        </div>
      </footer>

      {/* ── ECG draw animation ── */}
      <style jsx global>{`
        @keyframes ecg-draw {
          0%   { stroke-dashoffset: 600; opacity: 0; }
          10%  { opacity: 1; }
          80%  { stroke-dashoffset: 0; opacity: 1; }
          100% { stroke-dashoffset: 0; opacity: 0.3; }
        }
        .animate-ecg-draw {
          stroke-dasharray: 600;
          stroke-dashoffset: 600;
          animation: ecg-draw 4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
