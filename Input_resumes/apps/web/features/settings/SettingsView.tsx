'use client';

import React, { useState } from 'react';
import { Sliders, ShieldCheck, Cpu, Database, Save, CheckCircle2, Trash2 } from 'lucide-react';
import { clearAllCandidates } from '../../lib/api';

export const SettingsView: React.FC = () => {
  const [minTeachingYears, setMinTeachingYears] = useState(2.0);
  const [minPublications, setMinPublications] = useState(2);
  const [passingScore, setPassingScore] = useState(70.0);
  const [autoApproveConfidence, setAutoApproveConfidence] = useState(0.85);
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Title */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-900 tracking-tight">System Configuration & Screening Rules</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure transparent evaluation weights, confidence floors, and institutional taxonomy criteria.
          </p>
        </div>
        <button
          onClick={handleSave}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer transition-colors"
        >
          {isSaved ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Save className="w-3.5 h-3.5" />}
          <span>{isSaved ? 'Rules Saved' : 'Save Changes'}</span>
        </button>
      </div>

      {/* Rules Editor */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Sliders className="w-4 h-4 text-blue-900" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">Academic Screening Thresholds</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <label className="font-semibold text-slate-800">Minimum Teaching Experience (Years)</label>
            <p className="text-[11px] text-slate-500">Mandatory academic instruction threshold</p>
            <input
              type="number"
              step="0.5"
              min="0"
              value={minTeachingYears}
              onChange={(e) => setMinTeachingYears(Number(e.target.value))}
              className="mt-1 w-full p-2 bg-white border border-slate-200 rounded text-xs font-mono font-bold"
            />
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <label className="font-semibold text-slate-800">Minimum Peer-Reviewed Publications</label>
            <p className="text-[11px] text-slate-500">Indexed in Scopus, SCI, or IEEE</p>
            <input
              type="number"
              min="0"
              value={minPublications}
              onChange={(e) => setMinPublications(Number(e.target.value))}
              className="mt-1 w-full p-2 bg-white border border-slate-200 rounded text-xs font-mono font-bold"
            />
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <label className="font-semibold text-slate-800">Overall Passing Score (%)</label>
            <p className="text-[11px] text-slate-500">Weighted score required for eligibility</p>
            <input
              type="number"
              min="50"
              max="100"
              value={passingScore}
              onChange={(e) => setPassingScore(Number(e.target.value))}
              className="mt-1 w-full p-2 bg-white border border-slate-200 rounded text-xs font-mono font-bold"
            />
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <label className="font-semibold text-slate-800">Auto-Approval Confidence Floor</label>
            <p className="text-[11px] text-slate-500">Below this floor, routed to Human Review Queue</p>
            <input
              type="number"
              step="0.05"
              min="0.5"
              max="1.0"
              value={autoApproveConfidence}
              onChange={(e) => setAutoApproveConfidence(Number(e.target.value))}
              className="mt-1 w-full p-2 bg-white border border-slate-200 rounded text-xs font-mono font-bold"
            />
          </div>
        </div>
      </div>

      {/* Model & Infrastructure Info */}
      {/* Model & Infrastructure Info */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3 text-xs">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Cpu className="w-4 h-4 text-blue-900" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">Active Integrations & Engine</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-600">
          <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-200">
            <span>Groq Reasoning Model</span>
            <span className="font-mono font-bold text-slate-900">openai/gpt-oss-20b</span>
          </div>

          <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-200">
            <span>Groq Vision Model</span>
            <span className="font-mono font-bold text-slate-900">qwen/qwen3.8-27b</span>
          </div>

          <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-200">
            <span>Source Resumes Directory</span>
            <span className="font-mono text-slate-800 text-[11px]">c:/Users/.../Prj4/Input_resumes</span>
          </div>

          <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-200">
            <span>Database Backend</span>
            <span className="font-mono text-slate-800 text-[11px]">SQLite (Local High-Speed)</span>
          </div>
        </div>
      </div>

      {/* Database & Storage Management */}
      <div className="bg-white rounded-xl border border-rose-200 p-5 shadow-xs space-y-3 text-xs">
        <div className="flex items-center justify-between pb-3 border-b border-rose-100">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-rose-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-rose-900">Database & Cache Management</h2>
          </div>
          <button
            onClick={async () => {
              if (confirm("Are you sure you want to clear all candidate records and processed cache? Your original source PDF files will NOT be deleted.")) {
                const ok = await clearAllCandidates();
                if (ok) {
                  alert("Successfully cleared all previous resumes and screening data.");
                  window.location.reload();
                }
              }
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear All Resumes & Data</span>
          </button>
        </div>
        <p className="text-slate-600 leading-relaxed">
          Clears all processed candidate profiles, educational breakdowns, screening scores, and review logs from the relational database and disk cache. This gives you a completely clean slate for fresh processing without modifying or deleting any original input files.
        </p>
      </div>
    </div>
  );
};
