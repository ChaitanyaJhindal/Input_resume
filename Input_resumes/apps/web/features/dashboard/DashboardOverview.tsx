'use client';

import React from 'react';
import { 
  Users, CheckCircle2, AlertTriangle, XCircle, Clock, 
  GraduationCap, Building2, BookOpen, ArrowRight, Sparkles
} from 'lucide-react';
import { Candidate, AnalyticsOverview } from '../../types/candidate';

interface DashboardOverviewProps {
  analytics: AnalyticsOverview;
  recentCandidates: Candidate[];
  onSelectCandidate: (candidateId: string) => void;
  onNavigateToTab: (tab: any) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  analytics,
  recentCandidates,
  onSelectCandidate,
  onNavigateToTab
}) => {
  const { metrics, distributions } = analytics;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Faculty Recruitment Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time multimodal screening against institutional tenure & qualification criteria.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigateToTab('queue')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer transition-colors"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Review Queue ({metrics.needs_review})</span>
          </button>
          <button
            onClick={() => onNavigateToTab('library')}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer transition-colors"
          >
            <span>View Full Library</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Total Discovered</span>
            <Users className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{metrics.total_resumes}</div>
          <div className="mt-1 text-[11px] text-slate-500">Source directory pool</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Screened</span>
            <CheckCircle2 className="w-4 h-4 text-blue-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-blue-900">{metrics.processed}</div>
          <div className="mt-1 text-[11px] text-blue-600 font-medium">100% facts extracted</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Eligible</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-700">{metrics.eligible}</div>
          <div className="mt-1 text-[11px] text-emerald-600 font-medium">Passes mandatory rules</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Needs Review</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-600">{metrics.needs_review}</div>
          <div className="mt-1 text-[11px] text-amber-700 font-medium">Flagged for human audit</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Avg Teaching</span>
            <BookOpen className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{metrics.average_teaching_years} yrs</div>
          <div className="mt-1 text-[11px] text-slate-500">Academic classroom exp</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Avg Latency</span>
            <Clock className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">{metrics.average_processing_time_sec}s</div>
          <div className="mt-1 text-[11px] text-emerald-600 font-medium">JEV sub-second routing</div>
        </div>
      </div>

      {/* Middle Grid: Distributions & Fast Filters */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Highest Degree Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-blue-900" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">Degree Distribution</h2>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">N={metrics.processed}</span>
          </div>
          <div className="mt-4 space-y-3">
            {distributions.degree.map((d) => {
              const pct = metrics.processed > 0 ? Math.round((d.count / metrics.processed) * 100) : 0;
              return (
                <div key={d.name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-slate-700">{d.name}</span>
                    <span className="font-semibold text-slate-900">{d.count} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${d.name.includes('PhD') || d.name.includes('Doctorate') ? 'bg-blue-900' : 'bg-slate-400'}`} 
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Institution Taxonomy Classification */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-blue-900" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">Institution Category</h2>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">Taxonomy DB</span>
          </div>
          <div className="mt-4 space-y-2.5">
            {distributions.institution_category.slice(0, 5).map((inst) => (
              <div key={inst.name} className="flex items-center justify-between text-xs py-1 border-b border-slate-50 last:border-0">
                <span className="text-slate-600">{inst.name}</span>
                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-semibold font-mono text-[11px]">
                  {inst.count}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Experience Brackets */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-blue-900" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">Teaching Experience</h2>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">Non-overlapping</span>
          </div>
          <div className="mt-4 space-y-3">
            {distributions.experience.map((exp) => {
              const pct = metrics.processed > 0 ? Math.round((exp.count / metrics.processed) * 100) : 0;
              return (
                <div key={exp.bracket}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-slate-700">{exp.bracket}</span>
                    <span className="font-semibold text-slate-900">{exp.count} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-600 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Section: Recent Candidates Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">Recently Screened Candidates</h3>
            <p className="text-[11px] text-slate-500">Multimodal extracted profiles and rule evaluations</p>
          </div>
          <button
            onClick={() => onNavigateToTab('library')}
            className="text-xs font-semibold text-blue-900 hover:text-blue-700 flex items-center gap-1 cursor-pointer"
          >
            <span>View all</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-600 border-b border-slate-200 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-2.5 px-4">Candidate</th>
                <th className="py-2.5 px-4">Highest Degree</th>
                <th className="py-2.5 px-4">Institution</th>
                <th className="py-2.5 px-4 text-center">Category</th>
                <th className="py-2.5 px-4 text-center">Teaching Exp</th>
                <th className="py-2.5 px-4 text-center">Publications</th>
                <th className="py-2.5 px-4 text-center">Screening Status</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recentCandidates.slice(0, 5).map((cand) => (
                <tr key={cand.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-medium text-slate-900">
                    <div>{cand.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono">{cand.file_name}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-700 font-medium">
                    {cand.highest_degree || 'Unclassified'}
                  </td>
                  <td className="py-3 px-4 text-slate-600">
                    {cand.highest_institution || '-'}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-medium border border-slate-200">
                      {cand.highest_institution_category || 'Other'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center font-mono font-medium text-slate-800">
                    {cand.teaching_years} yrs
                  </td>
                  <td className="py-3 px-4 text-center font-mono font-medium text-slate-800">
                    {cand.publications_count}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {cand.eligibility_status === 'eligible' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3" /> Eligible
                      </span>
                    ) : cand.eligibility_status === 'needs_review' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        <AlertTriangle className="w-3 h-3" /> Needs Review
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200">
                        <XCircle className="w-3 h-3" /> Disqualified
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => onSelectCandidate(cand.id)}
                      className="px-2.5 py-1 text-xs font-medium text-blue-900 hover:bg-blue-50 rounded border border-blue-200 transition-colors cursor-pointer"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
