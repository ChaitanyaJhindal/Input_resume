"use client";

import React, { useState } from "react";
import {
  Search,
  Upload,
  RefreshCw,
  X,
  Briefcase,
  Loader2,
  Trash2,
} from "lucide-react";
import { JobDescription, SyncStatus } from "../types/candidate";
import { Button } from "./ui";

interface NavbarProps {
  activeTab: string;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSearchSubmit: () => void;
  onOpenUpload: () => void;
  onResetWorkspace: () => Promise<void>;
  onTriggerSync: () => void;
  syncStatus: SyncStatus | null;
  jds: JobDescription[];
  activeJdId: string | null;
  onSelectActiveJd: (jdId: string | null) => void;
  isOffline?: boolean;
}

const TAB_TITLES: Record<string, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Recruitment Overview",
    subtitle:
      "Dynamic candidate fit insights, academic profiles, and pipeline telemetry",
  },
  jds: {
    title: "Job Descriptions & Rubrics",
    subtitle:
      "Upload JDs, tune evaluation weights, and run holistic candidate matching",
  },
  candidates: {
    title: "Candidate Pool",
    subtitle:
      "Search, filter, verify links, and approve applicants dynamically",
  },
  review: {
    title: "Human Review Queue",
    subtitle: "Verify low-confidence extractions and rule edge cases",
  },
  compare: {
    title: "Candidate Comparison",
    subtitle: "Side-by-side qualification matrix across selected applicants",
  },
  analytics: {
    title: "Analytics & Telemetry",
    subtitle:
      "Rule pass rates, grounding quality, and hybrid model execution metrics",
  },
  settings: {
    title: "Configuration & Rules",
    subtitle:
      "Screening thresholds, LLM routing, prompt templates, and system status",
  },
};

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  onOpenUpload,
  onResetWorkspace,
  onTriggerSync,
  syncStatus,
  jds,
  activeJdId,
  onSelectActiveJd,
  isOffline,
}) => {
  const [confirmReset, setConfirmReset] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const meta = TAB_TITLES[activeTab] ?? TAB_TITLES.dashboard;
  const isSyncing = Boolean(syncStatus?.running);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      onSearchSubmit();
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200/80 px-5 flex items-center justify-between gap-3 shrink-0">
      <div className="min-w-0 flex items-center gap-3">
        <div className="min-w-0">
          <h1 className="text-[15px] font-bold text-slate-900 truncate">
            {meta.title}
          </h1>
          <p className="text-xs text-slate-500 truncate hidden sm:block">
            {meta.subtitle}
          </p>
        </div>

        <div className="hidden md:flex items-center gap-1.5 pl-3 border-l border-slate-200/80">
          <Briefcase
            className={`w-3.5 h-3.5 shrink-0 ${
              activeJdId ? "text-navy-900" : "text-slate-400"
            }`}
            strokeWidth={1.5}
          />
          <select
            value={activeJdId ?? ""}
            onChange={(e) =>
              onSelectActiveJd(e.target.value ? e.target.value : null)
            }
            aria-label="Active evaluation Job Description"
            className={`text-xs font-medium rounded-md px-2.5 py-1.5 max-w-[220px] border transition focus:outline-none focus:border-navy-900 ${
              activeJdId
                ? "bg-navy-50/60 border-navy-200 text-navy-900"
                : "bg-slate-50 border-slate-200/80 text-slate-700"
            }`}
          >
            <option value="">Baseline Pool Rules (No JD)</option>
            {jds.map((j) => (
              <option key={j.jd_id} value={j.jd_id}>
                JD: {j.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <div className="relative hidden md:block w-56 lg:w-64">
          <Search
            className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
            strokeWidth={1.5}
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search candidate, degree, skill..."
            aria-label="Global candidate search"
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-slate-50 border border-slate-200/80 rounded-md text-slate-800 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-navy-900 focus:ring-2 focus:ring-navy-900/10 transition"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" strokeWidth={1.5} />
            </button>
          )}
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={onTriggerSync}
          disabled={isSyncing || isOffline}
          title={
            isSyncing
              ? `Processing ${syncStatus?.current_file || "resumes"}`
              : "Scan Input_resumes/ for new or unprocessed CVs"
          }
        >
          {isSyncing ? (
            <>
              <Loader2
                className="w-3.5 h-3.5 animate-spin text-navy-900"
                strokeWidth={1.5}
              />
              <span className="font-mono tabular-nums">
                Syncing {syncStatus?.completed ?? 0}/{syncStatus?.total ?? 0}
              </span>
            </>
          ) : (
            <>
              <RefreshCw
                className="w-3.5 h-3.5 text-slate-500"
                strokeWidth={1.5}
              />
              <span className="hidden sm:inline">Sync Folder</span>
            </>
          )}
        </Button>

        {confirmReset ? (
          <div className="inline-flex items-center gap-1">
            <Button
              variant="dangerSolid"
              size="xs"
              disabled={isResetting}
              onClick={async () => {
                setIsResetting(true);
                try {
                  await onResetWorkspace();
                  setConfirmReset(false);
                } finally {
                  setIsResetting(false);
                }
              }}
            >
              {isResetting ? "Clearing..." : "Confirm Clear"}
            </Button>
            <Button
              variant="ghost"
              size="xs"
              disabled={isResetting}
              onClick={() => setConfirmReset(false)}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setConfirmReset(true)}
            disabled={isSyncing || isOffline}
            title="Clear all candidates, JDs, uploads, and processed cache"
          >
            <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
            <span className="hidden lg:inline">Clear All</span>
          </Button>
        )}

        <Button
          variant="primary"
          size="sm"
          onClick={onOpenUpload}
          disabled={isOffline}
        >
          <Upload className="w-3.5 h-3.5" strokeWidth={1.5} />
          <span>Upload Resumes</span>
        </Button>
      </div>
    </header>
  );
};
