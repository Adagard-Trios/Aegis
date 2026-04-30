"use client";

import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Settings, Wifi, Shield, Bell, Monitor, Bluetooth, Database, Cpu } from "lucide-react";
import { API_URL } from "../lib/api";

export default function SettingsPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Vest configuration, connectivity & system preferences
          </p>
        </motion.div>

        {/* Connection Settings */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-4">
            <Wifi className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Connection
            </h3>
          </div>
          <div className="space-y-4">
            {[
              { label: "BLE Device", value: "Aegis_SpO2_Live", icon: Bluetooth },
              { label: "Backend API", value: API_URL, icon: Database },
              { label: "Stream Rate", value: "10 Hz (SSE)", icon: Monitor },
              { label: "Sample Rate", value: "40 Hz (Sensor)", icon: Cpu },
            ].map((s) => (
              <div
                key={s.label}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <div className="flex items-center gap-2">
                  <s.icon className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-foreground">{s.label}</span>
                </div>
                <span className="text-xs text-muted-foreground font-mono bg-muted px-2 py-1 rounded">
                  {s.value}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Alerts & Notifications */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Alert Thresholds
            </h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { label: "Heart Rate", min: "40", max: "120", unit: "BPM" },
              { label: "SpO₂", min: "90", max: "100", unit: "%" },
              { label: "Temperature", min: "35.0", max: "38.5", unit: "°C" },
              { label: "Breathing Rate", min: "8", max: "25", unit: "br/min" },
              { label: "Spinal Angle", min: "-15", max: "15", unit: "°" },
              { label: "Fall Detection", min: "—", max: "Active", unit: "" },
            ].map((t) => (
              <div key={t.label} className="bg-muted/50 rounded px-3 py-3">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                  {t.label}
                </p>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-foreground font-mono">{t.min}</span>
                  <span className="text-muted-foreground">—</span>
                  <span className="text-foreground font-mono">{t.max}</span>
                  <span className="text-muted-foreground">{t.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* System Info */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              System Information
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Vest Version", value: "v2.4" },
              { label: "MCU", value: "ESP32-S3 Dual-Core" },
              { label: "OS", value: "FreeRTOS" },
              { label: "Sensors", value: "15 Active" },
              { label: "Backend", value: "FastAPI + SSE" },
              { label: "Frontend", value: "Next.js 16" },
            ].map((info) => (
              <div key={info.label} className="flex justify-between py-1">
                <span className="text-xs text-muted-foreground">{info.label}</span>
                <span className="text-xs text-foreground font-medium">{info.value}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
