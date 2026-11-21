'use client';

import React from 'react';
import { Search, Bell, ShieldCheck, RefreshCw, Sparkles, UploadCloud } from 'lucide-react';

interface NavbarProps {
  onSearch?: (term: string) => void;
  onRefresh?: () => void;
  isProcessing?: boolean;
  onOpenUpload?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onSearch, onRefresh, isProcessing = false, onOpenUpload }) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-900 flex items-center justify-center text-white font-bold text-base shadow-xs">
            FS
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 text-base tracking-tight">FacultyScreen</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                Decision Support
              </span>
            </div>
            <p className="text-[11px] text-slate-500 leading-tight">University Faculty Curation & Screening Platform</p>
          </div>
        </div>
      </div>

      <div className="flex-1 max-w-md mx-8">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search candidates by name, degree, institution, or keywords..."
            onChange={(e) => onSearch && onSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-700 focus:bg-white transition-all"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        {onOpenUpload && (
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors shadow-2xs cursor-pointer"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload Resumes</span>
          </button>
        )}

        <button
          onClick={onRefresh}
          disabled={isProcessing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin text-blue-600' : 'text-slate-500'}`} />
          <span>{isProcessing ? 'Processing...' : 'Sync Resumes'}</span>
        </button>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>JEV Fast Layer Active</span>
        </div>

        <div className="h-6 w-px bg-slate-200 mx-1"></div>

        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-medium text-xs">
            RC
          </div>
          <div className="text-left hidden md:block">
            <p className="text-xs font-semibold text-slate-800 leading-tight">Recruitment Chair</p>
            <p className="text-[10px] text-slate-500 leading-tight">Academic Affairs</p>
          </div>
        </div>
      </div>
    </header>
  );
};
