'use client';

import React from 'react';
import { BarChart3, Zap, ShieldCheck, Cpu, Clock, Layers } from 'lucide-react';
import { AnalyticsOverview } from '../../types/candidate';

interface AnalyticsViewProps {
  analytics: AnalyticsOverview;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({ analytics }) => {
  const { metrics, distributions, telemetry } = analytics;

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <h1 className="text-lg font-bold text-slate-900 tracking-tight">Recruitment Analytics & Telemetry</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Real-time metrics on candidate pool composition, qualification distributions, and JEV decision efficiency.
        </p>
      </div>

      {/* Decision Engine Telemetry Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Deterministic Hits</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900">{telemetry.deterministic_resolutions}</div>
          <div className="mt-1 text-[11px] text-emerald-600 font-medium">Resolved via local taxonomy DB (0ms)</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">JEV Fast Decisions</span>
            <Zap className="w-4 h-4 text-blue-600" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900">{telemetry.jev_decision_calls}</div>
          <div className="mt-1 text-[11px] text-blue-600 font-medium">TypeSafe structured checks</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Groq Vision Calls</span>
            <Cpu className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900">{telemetry.groq_api_calls}</div>
          <div className="mt-1 text-[11px] text-indigo-600 font-medium">Multimodal OCR visual parsing</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider">Escalation Rate</span>
            <Layers className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-900">
            {telemetry.jev_decision_calls > 0 ? `${Math.round((telemetry.escalations / telemetry.jev_decision_calls) * 100)}%` : '0%'}
          </div>
          <div className="mt-1 text-[11px] text-slate-500">Ambiguity escalated to LLM</div>
        </div>
      </div>

      {/* Main Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Institutional Classification Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 pb-3 border-b border-slate-100">
            Institutional Taxonomy Breakdown
          </h3>
          <div className="mt-4 space-y-3">
            {distributions.institution_category.map((inst) => {
              const maxCount = Math.max(...distributions.institution_category.map(i => i.count), 1);
              const widthPct = Math.round((inst.count / maxCount) * 100);

              return (
                <div key={inst.name}>
                  <div className="flex justify-between text-xs mb-1 font-medium">
                    <span className="text-slate-700">{inst.name}</span>
                    <span className="font-mono text-slate-900 font-bold">{inst.count}</span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-900 rounded-full transition-all" style={{ width: `${widthPct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Experience Stratification */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 pb-3 border-b border-slate-100">
            Classroom Teaching Experience Stratification
          </h3>
          <div className="mt-4 space-y-3">
            {distributions.experience.map((exp) => {
              const total = metrics.processed || 1;
              const widthPct = Math.round((exp.count / total) * 100);

              return (
                <div key={exp.bracket}>
                  <div className="flex justify-between text-xs mb-1 font-medium">
                    <span className="text-slate-700">{exp.bracket}</span>
                    <span className="font-mono text-slate-900 font-bold">{exp.count} ({widthPct}%)</span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-600 rounded-full transition-all" style={{ width: `${widthPct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
