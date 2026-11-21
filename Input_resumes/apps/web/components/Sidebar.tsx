'use client';

import React from 'react';
import {
  LayoutDashboard,
  Users,
  UserCheck,
  GitCompare,
  BarChart3,
  Sliders,
  FileText,
  AlertTriangle
} from 'lucide-react';

export type ScreenTab = 'overview' | 'library' | 'detail' | 'queue' | 'compare' | 'analytics' | 'settings';

interface SidebarProps {
  activeTab: ScreenTab;
  onTabChange: (tab: ScreenTab) => void;
  reviewQueueCount?: number;
  totalCandidatesCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  reviewQueueCount = 0,
  totalCandidatesCount = 0
}) => {
  const navItems = [
    { id: 'overview' as ScreenTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'library' as ScreenTab, label: 'Resume Library', icon: Users, badge: totalCandidatesCount || undefined },
    { id: 'queue' as ScreenTab, label: 'Screening Queue', icon: AlertTriangle, badge: reviewQueueCount || undefined, badgeColor: 'bg-amber-100 text-amber-800' },
    { id: 'compare' as ScreenTab, label: 'Compare Candidates', icon: GitCompare },
    { id: 'analytics' as ScreenTab, label: 'Analytics', icon: BarChart3 },
    { id: 'settings' as ScreenTab, label: 'Settings & Rules', icon: Sliders },
  ];

  return (
    <aside className="w-60 bg-white border-r border-slate-200 flex flex-col justify-between py-4 shrink-0 select-none">
      <div className="space-y-6">
        <div className="px-4">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 mb-2">
            Navigation
          </p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-blue-900 text-white shadow-xs'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                        isActive
                          ? 'bg-blue-800 text-white'
                          : item.badgeColor || 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="px-4">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 px-3 mb-2">
            Active Cycle
          </p>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Posting</span>
              <span className="font-semibold text-slate-800">Faculty 2026</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Department</span>
              <span className="font-semibold text-slate-800">CS & AI Dept</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Mandatory Ph.D.</span>
              <span className="text-emerald-700 font-bold">Enforced</span>
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 pt-4 border-t border-slate-100">
        <div className="flex items-center gap-2 px-3 py-2 text-slate-500 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-[11px]">Pipeline v1.0.0 Ready</span>
        </div>
      </div>
    </aside>
  );
};
