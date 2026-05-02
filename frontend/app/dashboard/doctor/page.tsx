"use client";

import DashboardLayout from "../components/DashboardLayout";
import { DashboardHeader, VestStatusCard } from "../components/DashboardHeader";
import { SystemSummary } from "../components/SystemSummary";
import { BiometricGrid } from "../components/BiometricGrid";
import { LiveWaveforms } from "../components/LiveWaveforms";
import { ExpertSummaryCards } from "../components/ExpertSummaryCards";
import { MedVerseDigitalTwin } from "../components/MedVerseDigitalTwin";
import { SimulationControls } from "../components/SimulationControls";
import { useVestStream } from "../hooks/useVestStream";
import { Radio, Shield, Stethoscope } from "lucide-react";

export default function DoctorDashboard() {
  const { data } = useVestStream();

  return (
    <DashboardLayout>
      <div className="p-4 md:p-6 space-y-6 pt-14 md:pt-6 flex flex-col h-[calc(100vh-2rem)] overflow-hidden">
        <DashboardHeader />

        <div className="flex-1 w-full flex flex-col xl:flex-row gap-6 overflow-hidden">

          {/* Left — Digital Twin */}
          <div className="w-full xl:w-2/5 flex flex-col h-full min-h-[500px] xl:min-h-0 bg-black/5 rounded-2xl border border-border/50 overflow-hidden relative">
            <MedVerseDigitalTwin />
          </div>

          {/* Right — Analytics */}
          <div className="w-full xl:w-3/5 flex flex-col h-full overflow-y-auto pr-2 space-y-6 scrollbar-hide">

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <SystemSummary />
              <VestStatusCard />
            </div>

            <SimulationControls />

            <div>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-4 h-4 text-primary" />
                <h2 className="font-display text-lg font-semibold text-foreground tracking-tight">
                  Live Comprehensive Biometrics
                </h2>
              </div>
              <BiometricGrid data={data} />
            </div>

            <div>
              <div className="flex items-center gap-2 mb-4">
                <Radio className="w-4 h-4 text-primary animate-data-pulse" />
                <h2 className="font-display text-lg font-semibold text-foreground tracking-tight">
                  Telemetry Waveforms
                </h2>
              </div>
              <LiveWaveforms />
            </div>

            <div className="pb-8">
              <div className="flex items-center gap-2 mb-4">
                <Stethoscope className="w-4 h-4 text-primary" />
                <h2 className="font-display text-lg font-semibold text-foreground tracking-tight">
                  Expert Agent Anomalies
                </h2>
              </div>
              <ExpertSummaryCards />
            </div>

          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
