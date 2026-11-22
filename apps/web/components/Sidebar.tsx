"use client";

import React from "react";
import {
  LayoutDashboard,
  Users,
  ClipboardCheck,
  GitCompare,
  BarChart3,
  Settings,
  GraduationCap,
  Briefcase,
} from "lucide-react";
import { SystemStatus } from "../types/candidate";

interface SidebarProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  totalCandidates: number;
  reviewCount: number;
  compareCount: number;
  jdsCount: number;
  systemStatus: SystemStatus | null;
  isOffline: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  totalCandidates,
  reviewCount,
  compareCount,
  jdsCount,
  systemStatus,
  isOffline,
}) => {
  const navItems = [
    { id: "dashboard", label: "Overview", icon: LayoutDashboard },
    {
      id: "jds",
      label: "Job Descriptions",
      icon: Briefcase,
      badge: jdsCount > 0 ? jdsCount : undefined,
      badgeVariant: "navy" as const,
    },
    {
      id: "candidates",
      label: "Candidate Pool",
      icon: Users,
      badge: totalCandidates > 0 ? totalCandidates : undefined,
      badgeVariant: "neutral" as const,
    },
    {
      id: "review",
      label: "Review Queue",
      icon: ClipboardCheck,
      badge: reviewCount > 0 ? reviewCount : undefined,
      badgeVariant: "amber" as const,
    },
    {
      id: "compare",
      label: "Compare",
      icon: GitCompare,
      badge: compareCount > 0 ? compareCount : undefined,
      badgeVariant: "navy" as const,
    },
    { id: "analytics", label: "Analytics", icon: BarChart3 },
    { id: "settings", label: "Rules & Config", icon: Settings },
  ];

  return (
    <aside className="w-60 bg-white text-slate-700 flex flex-col shrink-0 border-r border-slate-200/80">
      <div className="h-16 px-4 flex items-center gap-2.5 border-b border-slate-200/80">
        <div className="w-8 h-8 rounded-md bg-navy-900 flex items-center justify-center text-white shrink-0">
          <GraduationCap className="w-4 h-4" strokeWidth={1.5} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-display font-bold text-slate-900 tracking-tight truncate">
            FacultyScreen
          </div>
          <div className="text-[11px] text-slate-500 truncate">
            Academic Screening
          </div>
        </div>
      </div>

      <nav
        className="flex-1 px-3 py-4 space-y-1 overflow-y-auto"
        aria-label="Main navigation"
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-[13px] transition cursor-pointer ${
                isActive
                  ? "bg-navy-900/[0.06] text-navy-900 font-semibold border border-navy-900/15"
                  : "text-slate-600 font-medium hover:text-slate-900 hover:bg-slate-50 border border-transparent"
              }`}
            >
              <span className="flex items-center gap-2.5 min-w-0">
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    isActive ? "text-navy-900" : "text-slate-400"
                  }`}
                  strokeWidth={1.5}
                />
                <span className="truncate">{item.label}</span>
              </span>

              {item.badge !== undefined && (
                <span
                  className={`text-[11px] font-mono font-semibold px-1.5 py-0.25 rounded-full border tabular-nums ${
                    item.badgeVariant === "amber"
                      ? "bg-amber-50 text-amber-800 border-amber-200/80"
                      : item.badgeVariant === "navy"
                      ? "bg-navy-50 text-navy-900 border-navy-200/80"
                      : "bg-slate-100 text-slate-600 border-slate-200/80"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-3.5 border-t border-slate-200/80 bg-slate-50/70">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Backend Status
          </span>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium">
            <span
              className={`w-2 h-2 rounded-full ${
                isOffline
                  ? "bg-rose-600"
                  : systemStatus?.mock_mode
                  ? "bg-amber-500"
                  : "bg-emerald-600"
              }`}
            />
            <span
              className={
                isOffline
                  ? "text-rose-700"
                  : systemStatus?.mock_mode
                  ? "text-amber-700"
                  : "text-emerald-700"
              }
            >
              {isOffline
                ? "Offline"
                : systemStatus?.mock_mode
                ? "Mock Mode"
                : "Live Engine"}
            </span>
          </span>
        </div>

        {systemStatus && !isOffline ? (
          <div className="space-y-1 text-[11px] text-slate-500">
            <div className="flex justify-between">
              <span>Groq API Keys</span>
              <span className="text-slate-800 font-mono tabular-nums">
                {systemStatus.groq_keys_count} active
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="shrink-0">JEV Gate</span>
              <span className="text-slate-800 font-mono tabular-nums truncate">
                {systemStatus.typesafe_configured ? "Configured" : "Fallback"}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-[11px] text-slate-500">
            {isOffline ? "API server unreachable" : "Checking engine status..."}
          </p>
        )}
      </div>
    </aside>
  );
};
