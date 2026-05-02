"use client";

import { motion } from "framer-motion";
import { usePathname, useRouter } from "next/navigation";
import {
  Heart,
  Wind,
  Brain,
  Baby,
  BarChart3,
  Settings,
  History,
  ChevronLeft,
  ChevronRight,
  Stethoscope,
  Thermometer,
  Users,
  Bell,
  FileJson,
  Box,
  ClipboardList,
  Shield,
  Wifi,
} from "lucide-react";

const navItems = [
  { icon: BarChart3, label: "Dashboard", path: "/" },
  { icon: Box, label: "Digital Twin", path: "/digital-twin" },
  { icon: Users, label: "Patients", path: "/patients" },
  { icon: Bell, label: "Alerts", path: "/alerts" },
  { icon: ClipboardList, label: "Handoff", path: "/handoff" },
  { icon: Heart, label: "Cardiology", path: "/cardiology" },
  { icon: Wind, label: "Respiratory", path: "/respiratory" },
  { icon: Brain, label: "Neurology", path: "/neurology" },
  { icon: Baby, label: "Obstetrics", path: "/obstetrics" },
  { icon: Stethoscope, label: "Diagnostics", path: "/diagnostics" },
  { icon: Thermometer, label: "Environment", path: "/environment" },
  { icon: History, label: "History", path: "/history" },
  { icon: FileJson, label: "FHIR Export", path: "/fhir-export" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

interface MedVerseSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}

export function MedVerseSidebar({
  collapsed,
  onToggle,
  onNavigate,
}: MedVerseSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();

  const handleNav = (path: string) => {
    router.push(path);
    onNavigate?.();
  };

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 220 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="h-screen bg-sidebar flex flex-col border-r border-sidebar-border relative z-20 flex-shrink-0"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-sidebar-border">
        <div className="w-8 h-8 rounded bg-primary flex items-center justify-center flex-shrink-0">
          <Shield className="w-5 h-5 text-primary-foreground" />
        </div>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-display font-bold text-lg text-sidebar-foreground tracking-wide"
          >
            AEGIS
          </motion.span>
        )}
      </div>

      {/* Status indicator */}
      <div className="px-4 py-3 border-b border-sidebar-border">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-vital-green animate-pulse-glow flex-shrink-0" />
          {!collapsed && (
            <span className="text-xs text-sidebar-foreground/70 font-body">
              Aegis Vest Online
            </span>
          )}
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-3 space-y-1 px-2 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <button
              key={item.label}
              onClick={() => handleNav(item.path)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md transition-all duration-150 group relative cursor-pointer
                ${
                  isActive
                    ? "bg-sidebar-accent text-primary"
                    : "text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                }`}
            >
              <item.icon
                className={`w-5 h-5 flex-shrink-0 ${
                  isActive ? "text-primary" : ""
                }`}
              />
              {!collapsed && (
                <span className="text-sm font-medium truncate">
                  {item.label}
                </span>
              )}
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute left-0 w-0.5 h-6 bg-primary rounded-r"
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* Wifi status */}
      <div className="px-4 py-3 border-t border-sidebar-border">
        <div className="flex items-center gap-2">
          <Wifi className="w-4 h-4 text-primary flex-shrink-0" />
          {!collapsed && (
            <span className="text-xs text-sidebar-foreground/60">
              Edge Tier • 4ms
            </span>
          )}
        </div>
      </div>

      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-secondary border border-sidebar-border flex items-center justify-center text-sidebar-foreground/60 hover:text-primary transition-colors hidden md:flex cursor-pointer"
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3" />
        ) : (
          <ChevronLeft className="w-3 h-3" />
        )}
      </button>
    </motion.aside>
  );
}
