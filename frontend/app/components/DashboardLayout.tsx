"use client";

import { useState } from "react";
import { AegisSidebar } from "./AegisSidebar";
import { ExpertChatPanel } from "./ExpertChatPanel";
import { Menu } from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile menu button */}
      <button
        onClick={() => setMobileNavOpen(!mobileNavOpen)}
        className="fixed top-3 left-3 z-50 w-10 h-10 rounded-lg bg-secondary flex items-center justify-center text-secondary-foreground shadow-lg md:hidden"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-[260px] transform transition-transform duration-200 md:hidden ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <AegisSidebar
          collapsed={false}
          onToggle={() => setMobileNavOpen(false)}
          onNavigate={() => setMobileNavOpen(false)}
        />
      </div>

      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <AegisSidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      <main className="flex-1 overflow-y-auto">{children}</main>
      <ExpertChatPanel />
    </div>
  );
}
