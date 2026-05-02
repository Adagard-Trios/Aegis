"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { motion, useScroll, useTransform, useInView, useMotionValue, animate } from "framer-motion";
import {
  ArrowRight, ChevronDown, Github, Heart, Wind, Brain, Baby, Eye,
  Stethoscope, Zap, Activity, Wifi, ShieldCheck, Cpu, Sparkles as SparkIcon,
} from "lucide-react";

// Three.js + drei pull WebGL-only modules that crash during static
// prerender on Vercel — load them browser-side only.
const HeroCanvas = dynamic(() => import("./components/HeroCanvas"), {
  ssr: false,
  loading: () => null,
});
const VestSectionCanvas = dynamic(() => import("./components/VestSectionCanvas"), {
  ssr: false,
  loading: () => null,
});

// SmoothScroll uses Lenis which touches `window`; isolate it from SSR too.
const SmoothScroll = dynamic(
  () => import("./components/SmoothScroll").then((m) => m.SmoothScroll),
  { ssr: false }
);


// ──────────────────────────────────────────────────────────────────────────
// 1.  TOP NAV  (blurred, sticky)
// ──────────────────────────────────────────────────────────────────────────

function TopNav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-black/70 backdrop-blur-xl border-b border-white/5"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 h-16">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-[0_0_24px_rgba(168,85,247,0.5)] group-hover:shadow-[0_0_36px_rgba(168,85,247,0.7)] transition-shadow">
            <SparkIcon className="w-4 h-4 text-white" />
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-white">
            MedVerse
          </span>
        </Link>
        <nav className="hidden md:flex items-center gap-8 text-sm text-white/60">
          <a href="#telemetry" className="hover:text-white transition-colors">Live</a>
          <a href="#specialists" className="hover:text-white transition-colors">Specialists</a>
          <a href="#vest" className="hover:text-white transition-colors">Hardware</a>
          <a href="https://github.com/Adagard-Trios/Aegis" target="_blank" rel="noreferrer" className="hover:text-white transition-colors flex items-center gap-1.5">
            <Github className="w-3.5 h-3.5" /> GitHub
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="text-sm text-white/70 hover:text-white px-3 py-1.5 rounded-md transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="text-sm font-semibold bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white px-4 py-1.5 rounded-md shadow-[0_0_20px_rgba(168,85,247,0.45)] hover:shadow-[0_0_28px_rgba(168,85,247,0.65)] transition-shadow"
          >
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}


// ──────────────────────────────────────────────────────────────────────────
// 2.  HERO  —  3D vest background, parallax title, CTAs
// ──────────────────────────────────────────────────────────────────────────

function Hero() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const titleY = useTransform(scrollYProgress, [0, 1], ["0%", "-40%"]);
  const titleOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);
  const vestOpacity = useTransform(scrollYProgress, [0, 0.7], [0.5, 0]);
  const vestY = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);

  return (
    <section
      ref={ref}
      className="relative h-screen w-full overflow-hidden flex items-center justify-center"
    >
      {/* Radial purple aurora */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_30%,rgba(168,85,247,0.18),transparent_60%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_80%,rgba(217,70,239,0.12),transparent_55%)]" />

      {/* 3D vest, parallax-faded — dynamically loaded so SSR doesn't choke on WebGL */}
      <motion.div style={{ opacity: vestOpacity, y: vestY }} className="absolute inset-0 pointer-events-none">
        <HeroCanvas />
      </motion.div>

      {/* Hero text */}
      <motion.div
        style={{ y: titleY, opacity: titleOpacity }}
        className="relative z-10 text-center px-6 max-w-5xl"
      >
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-violet-500/30 bg-violet-500/5 text-[11px] font-semibold uppercase tracking-wider text-violet-300"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
          Multi-agent clinical intelligence
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.7 }}
          className="font-display text-6xl md:text-8xl lg:text-9xl font-bold tracking-tight text-white leading-[0.95]"
        >
          The wearable that<br />
          <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-violet-400 bg-clip-text text-transparent">
            thinks like a clinician.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="mt-8 text-lg md:text-xl text-white/60 max-w-2xl mx-auto leading-relaxed"
        >
          15-sensor wearable + 12 specialist AI agents + a 3D digital twin.
          From raw biosignal to clinician decision in under a second.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55, duration: 0.5 }}
          className="mt-10 flex items-center justify-center gap-3"
        >
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-semibold shadow-[0_0_36px_rgba(168,85,247,0.5)] hover:shadow-[0_0_56px_rgba(168,85,247,0.75)] transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            Start free
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <a
            href="#telemetry"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-white/15 text-white/80 hover:text-white hover:border-white/30 transition-all"
          >
            See it live
          </a>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute -bottom-32 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-white/30 text-xs"
        >
          <span>Scroll</span>
          <ChevronDown className="w-4 h-4 animate-bounce" />
        </motion.div>
      </motion.div>
    </section>
  );
}


// ──────────────────────────────────────────────────────────────────────────
// 3.  LIVE TELEMETRY SHOWCASE
// ──────────────────────────────────────────────────────────────────────────

function useTickingNumber(target: number, jitter: number) {
  const value = useMotionValue(target);
  useEffect(() => {
    let alive = true;
    const tick = () => {
      if (!alive) return;
      const next = target + (Math.random() - 0.5) * jitter * 2;
      animate(value, next, { duration: 0.8, ease: "easeOut" });
      setTimeout(tick, 1000);
    };
    tick();
    return () => { alive = false; };
  }, [target, jitter, value]);
  const [display, setDisplay] = useState(target);
  useEffect(() => {
    const unsub = value.on("change", (v) => setDisplay(Math.round(v * 10) / 10));
    return unsub;
  }, [value]);
  return display;
}

function ECGSparkline({ color = "#a855f7" }: { color?: string }) {
  const path = "M0,40 L20,40 L24,40 L28,8 L32,72 L36,24 L40,40 L60,40 L100,40 L104,40 L108,12 L112,68 L116,28 L120,40 L160,40 L200,40";
  return (
    <svg viewBox="0 0 200 80" className="w-full h-16" preserveAspectRatio="none">
      <defs>
        <linearGradient id="ecg-line" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={color} stopOpacity="0" />
          <stop offset="40%" stopColor={color} stopOpacity="1" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={path} fill="none" stroke="url(#ecg-line)" strokeWidth="1.8" />
    </svg>
  );
}

function TelemetrySection() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.3 });
  const hr = useTickingNumber(78, 4);
  const spo2 = useTickingNumber(98, 1);
  const rr = useTickingNumber(16, 2);
  const temp = useTickingNumber(36.8, 0.2);

  return (
    <section id="telemetry" ref={ref} className="relative py-32 px-6 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_50%,rgba(168,85,247,0.08),transparent_60%)] pointer-events-none" />

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <motion.div
          initial={{ opacity: 0, x: -24 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 mb-5 rounded-full border border-violet-500/30 bg-violet-500/5 text-[11px] font-semibold uppercase tracking-wider text-violet-300">
            <Activity className="w-3 h-3" /> Live telemetry
          </span>
          <h2 className="font-display text-4xl md:text-6xl font-bold tracking-tight text-white leading-tight mb-6">
            Every heartbeat,<br />streamed and explained.
          </h2>
          <p className="text-white/60 text-lg leading-relaxed mb-8 max-w-xl">
            The vest streams 30+ biosignals at 10 Hz over BLE. The backend runs DSP,
            ML adapters, and 12 specialist agents in parallel — and emits a clinical
            interpretation while you&apos;re still mid-breath.
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              { icon: Wifi, label: "10 Hz SSE telemetry" },
              { icon: Cpu, label: "30+ sensor channels" },
              { icon: Zap, label: "<1 s agent latency" },
              { icon: ShieldCheck, label: "JWT + FHIR R4" },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2.5 text-white/70 text-sm">
                <Icon className="w-4 h-4 text-violet-300 flex-shrink-0" />
                {label}
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 24 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="relative"
        >
          <div className="absolute -inset-4 rounded-3xl bg-gradient-to-br from-violet-500/20 via-fuchsia-500/10 to-transparent blur-2xl" />
          <div className="relative rounded-2xl border border-white/10 bg-black/60 backdrop-blur-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] uppercase tracking-wider text-emerald-300 font-semibold">
                  Streaming • patient_demo
                </span>
              </div>
              <span className="text-[10px] text-white/40 font-mono">10 Hz</span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-5">
              {[
                { label: "Heart rate", value: hr.toFixed(0), unit: "bpm", color: "text-rose-300" },
                { label: "SpO₂", value: spo2.toFixed(0), unit: "%", color: "text-sky-300" },
                { label: "Resp rate", value: rr.toFixed(0), unit: "rpm", color: "text-emerald-300" },
                { label: "Core temp", value: temp.toFixed(1), unit: "°C", color: "text-amber-300" },
              ].map((v) => (
                <div key={v.label} className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <div className="text-[10px] uppercase tracking-wider text-white/40 mb-1">{v.label}</div>
                  <div className="flex items-baseline gap-1">
                    <span className={`font-mono text-2xl font-bold ${v.color}`}>{v.value}</span>
                    <span className="text-xs text-white/40">{v.unit}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-white/40">ECG · Lead II</span>
                <span className="text-[10px] text-white/40 font-mono">{hr.toFixed(0)} bpm</span>
              </div>
              <ECGSparkline color="#a855f7" />
            </div>

            <div className="mt-4 rounded-xl border border-violet-500/30 bg-violet-500/5 p-3 flex items-start gap-2.5">
              <Stethoscope className="w-4 h-4 text-violet-300 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-white/80 leading-relaxed">
                <span className="text-violet-300 font-semibold">Cardiology agent:</span>{" "}
                Sinus rhythm. ST-segment isoelectric. HRV within normal range.
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}


// ──────────────────────────────────────────────────────────────────────────
// 4.  12 AI SPECIALISTS GRID
// ──────────────────────────────────────────────────────────────────────────

const SPECIALISTS: { name: string; tag: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { name: "Cardiology", tag: "ECG arrhythmia", icon: Heart },
  { name: "Cardiac Age", tag: "Vascular regression", icon: Heart },
  { name: "ECG Biometric", tag: "Identity verification", icon: ShieldCheck },
  { name: "Pulmonary", tag: "Lung sounds", icon: Wind },
  { name: "Stress / ANS", tag: "Autonomic state", icon: Activity },
  { name: "Neurology", tag: "Parkinson screen", icon: Brain },
  { name: "Obstetrics", tag: "Foetal CTG", icon: Baby },
  { name: "Preterm Labour", tag: "EHG predictor", icon: Baby },
  { name: "Bowel Motility", tag: "GI transit", icon: Activity },
  { name: "Dermatology", tag: "Skin disease", icon: Stethoscope },
  { name: "Ocular Disease", tag: "Retinal scan", icon: Eye },
  { name: "Retinal Age", tag: "Biological age", icon: Eye },
];

function SpecialistsSection() {
  return (
    <section id="specialists" className="relative py-32 px-6 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_30%,rgba(217,70,239,0.08),transparent_60%)] pointer-events-none" />

      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-3xl mx-auto mb-16"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 mb-5 rounded-full border border-violet-500/30 bg-violet-500/5 text-[11px] font-semibold uppercase tracking-wider text-violet-300">
            <Brain className="w-3 h-3" /> 12 specialist agents
          </span>
          <h2 className="font-display text-4xl md:text-6xl font-bold tracking-tight text-white leading-tight mb-5">
            One vest.<br />
            <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-violet-400 bg-clip-text text-transparent">
              Twelve clinicians.
            </span>
          </h2>
          <p className="text-white/60 text-lg leading-relaxed">
            Every snapshot fans out to twelve specialist agents in parallel.
            Cardiology reads the ECG, obstetrics parses CTG, neurology watches
            tremor and gait — all returning structured findings to the general physician.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {SPECIALISTS.map((s, i) => (
            <motion.div
              key={s.name}
              initial={{ opacity: 0, y: 24, scale: 0.95 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.45, delay: (i % 4) * 0.06 }}
              whileHover={{ y: -4 }}
              className="group relative rounded-xl border border-white/8 bg-white/[0.02] hover:bg-white/[0.04] hover:border-violet-500/40 backdrop-blur-sm p-5 transition-all overflow-hidden"
            >
              <div className="absolute -inset-px rounded-xl opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-br from-violet-500/20 via-transparent to-fuchsia-500/20 pointer-events-none" />
              <div className="relative flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-violet-500/10 border border-violet-500/20 group-hover:bg-violet-500/20 group-hover:shadow-[0_0_20px_rgba(168,85,247,0.4)] transition-all flex-shrink-0">
                  <s.icon className="w-4 h-4 text-violet-300" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-white leading-tight">{s.name}</h3>
                  <p className="text-[11px] text-white/50 mt-0.5">{s.tag}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}


// ──────────────────────────────────────────────────────────────────────────
// 5.  VEST DEEP-DIVE  —  crisp 3D + sensor callouts
// ──────────────────────────────────────────────────────────────────────────

function VestSection() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.25 });
  const callouts = [
    { sensor: "MAX30102", label: "PPG × 3 sites", side: "left", top: "18%" },
    { sensor: "AD8232", label: "3-lead ECG", side: "left", top: "38%" },
    { sensor: "MPU-6050", label: "Dual IMU posture", side: "left", top: "60%" },
    { sensor: "DS18B20", label: "Skin temperature × 3", side: "right", top: "22%" },
    { sensor: "BMP280", label: "Ambient pressure", side: "right", top: "44%" },
    { sensor: "INMP441", label: "I²S lung-sound mic", side: "right", top: "68%" },
  ];

  return (
    <section id="vest" ref={ref} className="relative py-32 px-6 overflow-hidden border-t border-white/5">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_50%,rgba(168,85,247,0.1),transparent_50%)] pointer-events-none" />

      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-3xl mx-auto mb-12"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 mb-5 rounded-full border border-violet-500/30 bg-violet-500/5 text-[11px] font-semibold uppercase tracking-wider text-violet-300">
            <Cpu className="w-3 h-3" /> Hardware
          </span>
          <h2 className="font-display text-4xl md:text-6xl font-bold tracking-tight text-white leading-tight mb-5">
            ESP32-S3.<br />
            15 sensors. <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-violet-400 bg-clip-text text-transparent">FreeRTOS.</span>
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.8 }}
          className="relative h-[520px] md:h-[620px] rounded-3xl border border-white/8 bg-gradient-to-b from-black/40 to-violet-950/30 overflow-hidden"
        >
          <VestSectionCanvas />

          {callouts.map((c, i) => (
            <motion.div
              key={c.sensor}
              initial={{ opacity: 0, x: c.side === "left" ? -16 : 16 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: 0.5 + i * 0.08, duration: 0.5 }}
              className={`hidden md:block absolute ${c.side === "left" ? "left-6" : "right-6"} z-10`}
              style={{ top: c.top }}
            >
              <div className="px-3 py-1.5 rounded-lg bg-black/70 backdrop-blur-md border border-violet-500/30 shadow-[0_0_24px_rgba(168,85,247,0.25)]">
                <div className="text-[10px] font-mono text-violet-300 font-bold tracking-wider">
                  {c.sensor}
                </div>
                <div className="text-[11px] text-white/80">{c.label}</div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}


// ──────────────────────────────────────────────────────────────────────────
// 6.  CTA + FOOTER
// ──────────────────────────────────────────────────────────────────────────

function CTAFooter() {
  return (
    <section className="relative py-32 px-6 border-t border-white/5">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_50%,rgba(168,85,247,0.15),transparent_60%)] pointer-events-none" />
      <div className="relative max-w-4xl mx-auto text-center">
        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="font-display text-4xl md:text-6xl font-bold tracking-tight text-white leading-tight mb-6"
        >
          Ready to read a patient<br />
          <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-violet-400 bg-clip-text text-transparent">in twelve dimensions?</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="text-white/60 text-lg mb-8"
        >
          Setup takes thirty seconds. The vest pairs over BLE, the dashboard streams immediately.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="flex items-center justify-center gap-3"
        >
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-7 py-3.5 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white font-semibold shadow-[0_0_36px_rgba(168,85,247,0.5)] hover:shadow-[0_0_56px_rgba(168,85,247,0.75)] transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            Create account
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 px-7 py-3.5 rounded-lg border border-white/15 text-white/80 hover:text-white hover:border-white/30 transition-all"
          >
            Sign in
          </Link>
        </motion.div>
      </div>

      <footer className="relative mt-32 pt-10 border-t border-white/5 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-white/40">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center">
              <SparkIcon className="w-3 h-3 text-white" />
            </div>
            <span>MedVerse · MIT licensed · © 2026</span>
          </div>
          <div className="flex items-center gap-5">
            <a href="https://github.com/Adagard-Trios/Aegis" target="_blank" rel="noreferrer" className="hover:text-white transition-colors flex items-center gap-1.5">
              <Github className="w-3.5 h-3.5" /> GitHub
            </a>
            <a href="#telemetry" className="hover:text-white transition-colors">Live</a>
            <a href="#specialists" className="hover:text-white transition-colors">Specialists</a>
            <a href="#vest" className="hover:text-white transition-colors">Hardware</a>
          </div>
        </div>
      </footer>
    </section>
  );
}


// ──────────────────────────────────────────────────────────────────────────
// PAGE
// ──────────────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <main className="relative min-h-screen bg-[#06060a] text-white overflow-x-hidden">
      <SmoothScroll />
      <TopNav />
      <Hero />
      <TelemetrySection />
      <SpecialistsSection />
      <VestSection />
      <CTAFooter />
    </main>
  );
}
