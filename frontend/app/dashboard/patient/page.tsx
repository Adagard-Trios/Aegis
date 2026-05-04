"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Heart, Wind, Thermometer, Activity, Bell, FileJson,
  Settings, LogOut, Shield, Wifi, WifiOff, AlertTriangle,
  Stethoscope, History,
} from "lucide-react";
import { useVestStream } from "../../hooks/useVestStream";
import { useAuth } from "../../hooks/useAuth";
import { useActivePatient } from "../../hooks/useActivePatient";
import { fetchAlerts, type Alert } from "../../lib/api";
import ImageUploadWidget from "../../components/ImageUploadWidget";

function VitalTile({
  label, value, unit, icon: Icon, color, normal,
}: {
  label: string; value: string | number; unit: string;
  icon: React.ComponentType<{ className?: string; color?: string; size?: number }>; color: string; normal?: boolean;
}) {
  return (
    <div className="relative flex flex-col gap-3 p-5 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm overflow-hidden group hover:border-primary/30 transition-all duration-300">
      <div className={`absolute top-0 right-0 w-24 h-24 rounded-full blur-3xl opacity-10 ${color.replace("text-", "bg-")}`} />
      <div className="flex items-center justify-between">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center bg-white/5 border border-white/10 ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
        {normal !== undefined && (
          <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
            normal ? "bg-vital-green/15 text-vital-green" : "bg-warning/15 text-warning"
          }`}>
            {normal ? "Normal" : "Watch"}
          </span>
        )}
      </div>
      <div>
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className={`font-display font-bold text-3xl ${color}`}>
          {value}
          <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
        </p>
      </div>
    </div>
  );
}

export default function PatientDashboard() {
  const { data, connected } = useVestStream();
  const { me, logout } = useAuth();
  const router = useRouter();
  const { patientId } = useActivePatient();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [activeTab, setActiveTab] = useState<"health" | "alerts" | "history" | "reports">("health");

  useEffect(() => {
    fetchAlerts({ unacknowledged: true, limit: 5 }).then(setAlerts).catch(() => {});
  }, []);

  const v = data?.vitals;
  const hr = v?.heart_rate ?? "--";
  const spo2 = v?.spo2 ?? "--";
  const br = v?.breathing_rate ?? "--";
  const hrv = v?.hrv_rmssd ? Math.round(v.hrv_rmssd) : "--";
  const temp = data?.temperature?.cervical ?? "--";

  const navItems = [
    { id: "health", label: "My Health", icon: Heart },
    { id: "alerts", label: "Alerts", icon: Bell },
    { id: "history", label: "History", icon: History },
    { id: "reports", label: "Reports", icon: FileJson },
  ] as const;

  return (
    <div className="min-h-screen bg-background flex">

      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-56 border-r border-sidebar-border bg-sidebar h-screen sticky top-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-4 h-16 border-b border-sidebar-border">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
            <Shield className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-display font-bold text-base text-sidebar-foreground tracking-wide">MEDVERSE</span>
        </div>

        {/* Connection */}
        <div className="px-4 py-3 border-b border-sidebar-border">
          <div className="flex items-center gap-2">
            {connected ? (
              <Wifi className="w-3.5 h-3.5 text-vital-green" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-muted-foreground" />
            )}
            <span className="text-xs text-sidebar-foreground/60">
              {connected ? "Vest streaming" : "Vest offline"}
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-2 space-y-1">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as typeof activeTab)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === id
                  ? "bg-sidebar-accent text-primary"
                  : "text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
              }`}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </button>
          ))}
        </nav>

        {/* Bottom */}
        <div className="px-3 py-3 border-t border-sidebar-border space-y-1">
          <button
            onClick={() => router.push("/settings")}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent/50 transition-all"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-rose-400/70 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-6 overflow-y-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">
              My Health
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {me?.user?.sub ? `Welcome back, ${me.user.sub}` : "Real-time vitals from your MedVerse vest"}
            </p>
          </div>
          <div className={`flex items-center gap-2 border rounded-full px-3 py-1.5 text-xs font-semibold ${
            connected
              ? "bg-vital-green/10 border-vital-green/30 text-vital-green"
              : "bg-rose-500/10 border-rose-500/30 text-rose-400"
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-vital-green animate-pulse" : "bg-rose-400"}`} />
            {connected ? "Live" : "Offline"}
          </div>
        </div>

        {/* Health tab */}
        {activeTab === "health" && (
          <div className="space-y-6">
            {/* Vitals grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <VitalTile label="Heart Rate" value={hr} unit="bpm" icon={Heart} color="text-red-400" normal={typeof hr === "number" && hr >= 60 && hr <= 100} />
              <VitalTile label="SpO₂" value={spo2} unit="%" icon={Activity} color="text-primary" normal={typeof spo2 === "number" && spo2 >= 95} />
              <VitalTile label="Breathing Rate" value={br} unit="/min" icon={Wind} color="text-accent" normal={typeof br === "number" && br >= 12 && br <= 20} />
              <VitalTile label="Body Temp" value={typeof temp === "number" ? temp.toFixed(1) : temp} unit="°C" icon={Thermometer} color="text-orange-400" normal={typeof temp === "number" && temp >= 36.0 && temp <= 37.5} />
            </div>

            {/* AI summary card */}
            <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Stethoscope className="w-4 h-4 text-primary" />
                <h2 className="font-display font-semibold text-foreground">AI Health Summary</h2>
                <span className="ml-auto text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-vital-green/15 text-vital-green">
                  Updated now
                </span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {connected
                  ? "Your vital signs are within the normal range. Heart rate and SpO₂ look healthy. No critical alerts at this time. Continue wearing your vest for continuous monitoring."
                  : "Your MedVerse vest is currently offline. Please ensure the vest is charged and within Bluetooth range to resume real-time monitoring."}
              </p>
            </div>

            {/* HRV */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs text-muted-foreground mb-1">HRV (RMSSD)</p>
                <p className="font-display font-bold text-2xl text-yellow-400">
                  {hrv} <span className="text-sm font-normal text-muted-foreground">ms</span>
                </p>
                <p className="text-xs text-muted-foreground mt-2">Heart rate variability — higher is generally healthier.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs text-muted-foreground mb-1">Signal quality</p>
                <p className="font-display font-bold text-2xl text-primary">
                  {data?.vitals?.signal_quality ?? "--"}
                </p>
                <p className="text-xs text-muted-foreground mt-2">Ensure the vest sensors are in firm contact with skin.</p>
              </div>
            </div>

            {/* Image upload — feeds the retina + skin runtime adapters */}
            <ImageUploadWidget patientId={patientId} />
          </div>
        )}

        {/* Alerts tab */}
        {activeTab === "alerts" && (
          <div className="space-y-3">
            <h2 className="font-display font-semibold text-foreground mb-4">Active Alerts</h2>
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
                <Bell className="w-8 h-8 opacity-30" />
                <p className="text-sm">No unacknowledged alerts</p>
              </div>
            ) : (
              alerts.map((a) => (
                <div key={a.id} className={`flex items-start gap-3 p-4 rounded-xl border ${
                  a.severity >= 8 ? "border-red-500/30 bg-red-500/5" :
                  a.severity >= 5 ? "border-warning/30 bg-warning/5" :
                  "border-white/10 bg-white/5"
                }`}>
                  <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                    a.severity >= 8 ? "text-red-400" : a.severity >= 5 ? "text-warning" : "text-muted-foreground"
                  }`} />
                  <div>
                    <p className="text-sm text-foreground font-medium">{a.message}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{a.source} · {new Date(a.created_at).toLocaleString()}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* History / Reports placeholders */}
        {(activeTab === "history" || activeTab === "reports") && (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground gap-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              {activeTab === "history" ? <History className="w-5 h-5 text-primary" /> : <FileJson className="w-5 h-5 text-primary" />}
            </div>
            <p className="font-display font-semibold text-foreground">Coming soon</p>
            <p className="text-sm">This section is under development.</p>
          </div>
        )}
      </main>
    </div>
  );
}
