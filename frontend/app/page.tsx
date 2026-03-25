"use client";

import DashboardLayout from "./components/DashboardLayout";
import { DashboardHeader, VestStatusCard } from "./components/DashboardHeader";
import { SystemSummary } from "./components/SystemSummary";
import { BiometricGrid } from "./components/BiometricGrid";
import { LiveWaveforms } from "./components/LiveWaveforms";
import { ExpertSummaryCards } from "./components/ExpertSummaryCards";
import { VestModel3D } from "./components/VestModel3D";
import { useVestStream } from "./hooks/useVestStream";
import { motion } from "framer-motion";
import { Radio, Shield, Stethoscope } from "lucide-react";

export default function HomePage() {
  const { data } = useVestStream();

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6">
        <DashboardHeader />

        {/* Hero Section */}
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
          <div className="xl:col-span-2 space-y-4">
            <SystemSummary />
            <VestStatusCard />
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="xl:col-span-3 relative rounded-lg overflow-hidden bg-card border border-border shadow-card min-h-[420px]"
          >
            <VestModel3D />
          </motion.div>
        </div>

        {/* Expert Summaries */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Stethoscope className="w-4 h-4 text-primary" />
            <h2 className="font-display text-lg font-semibold text-foreground tracking-tight">
              Expert Agent Summaries
            </h2>
          </div>
          <ExpertSummaryCards />
        </div>

        {/* Live Waveforms */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Radio className="w-4 h-4 text-primary animate-data-pulse" />
            <h2 className="font-display text-lg font-semibold text-foreground tracking-tight">
              Live Waveforms
            </h2>
          </div>
          <LiveWaveforms />
        </div>

        {/* Biometric Summary Cards */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-primary" />
            <h2 className="font-display text-lg font-semibold text-foreground tracking-tight">
              Biometric Summary
            </h2>
          </div>
          <BiometricGrid data={data} />
        </div>
      </div>
    </DashboardLayout>
  );
}
