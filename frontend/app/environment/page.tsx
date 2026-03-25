"use client";

import DashboardLayout from "../components/DashboardLayout";
import { motion } from "framer-motion";
import { Thermometer, Wind, Droplets, Sun, Cloud, AlertCircle } from "lucide-react";

export default function EnvironmentPage() {
  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-2xl font-bold text-foreground">
            Environmental Monitoring
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Ambient sensors, air quality monitoring & thermal mapping
          </p>
        </motion.div>

        {/* Environmental Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          {[
            { label: "Ambient Temp", value: "24.5", unit: "°C", icon: Thermometer },
            { label: "Humidity", value: "45", unit: "%", icon: Droplets },
            { label: "Air Quality", value: "Good", unit: "AQI", icon: Wind },
            { label: "UV Index", value: "2", unit: "Low", icon: Sun },
            { label: "Pressure", value: "1013", unit: "hPa", icon: Cloud },
            { label: "CO₂ Level", value: "420", unit: "ppm", icon: AlertCircle },
          ].map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-card border border-border rounded-md p-4 shadow-card text-center"
            >
              <m.icon className="w-5 h-5 text-primary mx-auto mb-2" />
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                {m.label}
              </p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="font-display text-2xl font-bold text-foreground">{m.value}</span>
                <span className="text-xs text-muted-foreground">{m.unit}</span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Skin Temperature Map */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-4">
            <Thermometer className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Skin Temperature Distribution (DS18B20 Array)
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { zone: "Left Axilla", temp: "36.5", status: "Normal" },
              { zone: "Right Axilla", temp: "36.6", status: "Normal" },
              { zone: "Cervical (C7)", temp: "36.8", status: "Normal" },
            ].map((z) => (
              <div key={z.zone} className="bg-muted/50 rounded-lg p-4 text-center">
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                  {z.zone}
                </p>
                <span className="font-display text-3xl font-bold text-foreground">
                  {z.temp}
                </span>
                <span className="text-sm text-muted-foreground ml-1">°C</span>
                <p className="text-[10px] text-accent font-semibold uppercase mt-2">
                  {z.status}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* PPG Onboard Temperatures */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-card border border-border rounded-md p-4 shadow-card"
        >
          <div className="flex items-center gap-2 mb-3">
            <Thermometer className="w-4 h-4 text-warning" />
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              PPG Sensor Onboard Temperature
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-muted/50 rounded-lg p-4 text-center">
              <p className="text-xs text-muted-foreground mb-1">Sensor 1</p>
              <span className="font-display text-2xl font-bold text-foreground">30.5</span>
              <span className="text-sm text-muted-foreground ml-1">°C</span>
            </div>
            <div className="bg-muted/50 rounded-lg p-4 text-center">
              <p className="text-xs text-muted-foreground mb-1">Sensor 2</p>
              <span className="font-display text-2xl font-bold text-foreground">31.2</span>
              <span className="text-sm text-muted-foreground ml-1">°C</span>
            </div>
          </div>
        </motion.div>
      </div>
    </DashboardLayout>
  );
}
