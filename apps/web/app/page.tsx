"use client";

import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import {
  AnalyticsOverview,
  Candidate,
  JDCandidatesSummary,
  JobDescription,
  ScreeningRulesResponse,
  SyncStatus,
  SystemStatus,
} from "../types/candidate";
import {
  API_BASE,
  clearAllCandidates,
  deleteCandidate,
  evaluateJD,
  fetchAnalyticsOverview,
  fetchCandidateDetail,
  fetchCandidates,
  fetchJDCandidates,
  fetchJDs,
  fetchReviewQueue,
  fetchScreeningRules,
  fetchSyncStatus,
  fetchSystemStatus,
  processAllResumes,
  resetWorkspace,
} from "../lib/api";
import { Navbar } from "../components/Navbar";
import { Sidebar } from "../components/Sidebar";
import { UploadModal } from "../components/UploadModal";
import { Button, Card } from "../components/ui";
import { DashboardOverview } from "../features/dashboard/DashboardOverview";
import { CandidateTable } from "../features/candidates/CandidateTable";
import { CandidateDetailView } from "../features/candidates/CandidateDetailView";
import { ReviewQueueView } from "../features/screening/ReviewQueueView";
import { CandidateComparisonView } from "../features/comparison/CandidateComparisonView";
import { AnalyticsView } from "../features/analytics/AnalyticsView";
import { SettingsView } from "../features/settings/SettingsView";
import { JDWorkspaceView } from "../features/jds/JDWorkspaceView";

export default function HomePage() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [reviewQueue, setReviewQueue] = useState<Candidate[]>([]);
  const [rulesConfig, setRulesConfig] = useState<ScreeningRulesResponse | null>(
    null
  );
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);

  // Dynamic JD Context
  const [jds, setJds] = useState<JobDescription[]>([]);
  const [activeJdId, setActiveJdId] = useState<string | null>(null);
  const [jdEvaluationsMap, setJdEvaluationsMap] = useState<
    Record<string, Candidate["jd_evaluation"]>
  >({});
  const [jdSummary, setJdSummary] = useState<JDCandidatesSummary | null>(null);

  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(
    null
  );
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const activeJd = jds.find((j) => j.jd_id === activeJdId) ?? null;

  const loadAllData = useCallback(
    async (overrideJdId?: string | null) => {
      const targetJd =
        overrideJdId !== undefined ? overrideJdId : activeJdId;
      setLoadError(null);
      try {
        const [
          candRes,
          analyticsRes,
          queueRes,
          rulesRes,
          sysRes,
          syncRes,
          jdsRes,
        ] = await Promise.all([
          fetchCandidates({ limit: 500 }),
          fetchAnalyticsOverview(),
          fetchReviewQueue(),
          fetchScreeningRules(),
          fetchSystemStatus(),
          fetchSyncStatus().catch(() => null),
          fetchJDs().catch(() => []),
        ]);

        setCandidates(candRes.candidates);
        setAnalytics(analyticsRes);
        setReviewQueue(queueRes);
        setRulesConfig(rulesRes);
        setSystemStatus(sysRes);
        if (syncRes) setSyncStatus(syncRes);
        setJds(jdsRes);

        if (targetJd) {
          try {
            const jdRes = await fetchJDCandidates(targetJd);
            const map: Record<string, Candidate["jd_evaluation"]> = {};
            for (const c of jdRes.candidates) {
              if (c.jd_evaluation) map[c.id] = c.jd_evaluation;
            }
            setJdEvaluationsMap(map);
            setJdSummary(jdRes.summary);
          } catch {
            setJdEvaluationsMap({});
            setJdSummary(null);
          }
        } else {
          setJdEvaluationsMap({});
          setJdSummary(null);
        }
      } catch (err) {
        setLoadError(
          err instanceof Error
            ? err.message
            : `Could not connect to backend API at ${API_BASE}`
        );
      } finally {
        setIsLoading(false);
      }
    },
    [activeJdId]
  );

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const [
          candRes,
          analyticsRes,
          queueRes,
          rulesRes,
          sysRes,
          syncRes,
          jdsRes,
        ] = await Promise.all([
          fetchCandidates({ limit: 500 }),
          fetchAnalyticsOverview(),
          fetchReviewQueue(),
          fetchScreeningRules(),
          fetchSystemStatus(),
          fetchSyncStatus().catch(() => null),
          fetchJDs().catch(() => []),
        ]);
        if (cancelled) return;
        setCandidates(candRes.candidates);
        setAnalytics(analyticsRes);
        setReviewQueue(queueRes);
        setRulesConfig(rulesRes);
        setSystemStatus(sysRes);
        if (syncRes) setSyncStatus(syncRes);
        setJds(jdsRes);
        setLoadError(null);
      } catch (err) {
        if (cancelled) return;
        setLoadError(
          err instanceof Error
            ? err.message
            : `Could not connect to backend API at ${API_BASE}`
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, []);

  const syncRunning = Boolean(syncStatus?.running);
  useEffect(() => {
    if (!syncRunning) return;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const latest = await fetchSyncStatus();
        if (cancelled) return;
        setSyncStatus(latest);
        if (!latest.running) {
          await loadAllData();
        }
      } catch {
        // Ignore transient errors
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [syncRunning, loadAllData]);

  const handleSelectActiveJd = async (jdId: string | null) => {
    setActiveJdId(jdId);
    await loadAllData(jdId);
    if (selectedCandidate) {
      try {
        const refreshed = await fetchCandidateDetail(selectedCandidate.id, jdId);
        setSelectedCandidate(refreshed);
      } catch {
        // Ignore
      }
    }
  };

  const hydratedCandidates: Candidate[] = activeJdId
    ? candidates.map((c) => ({
        ...c,
        jd_evaluation: jdEvaluationsMap[c.id] ?? c.jd_evaluation ?? null,
      }))
    : candidates;

  const handleSelectCandidate = async (cand: Candidate) => {
    setSelectedCandidate(cand);
    try {
      const hydrated = await fetchCandidateDetail(cand.id, activeJdId);
      setSelectedCandidate(hydrated);
    } catch {
      // Fallback
    }
  };

  const handleEvaluateSingleForActiveJd = async (candidateId: string) => {
    if (!activeJdId) return;
    await evaluateJD(activeJdId, [candidateId]);
    await loadAllData(activeJdId);
    const updated = await fetchCandidateDetail(candidateId, activeJdId);
    setSelectedCandidate(updated);
  };

  const handleToggleCompare = (id: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 4) return [...prev.slice(1), id];
      return [...prev, id];
    });
  };

  const handleTriggerSync = async () => {
    try {
      await processAllResumes(false);
      const status = await fetchSyncStatus();
      setSyncStatus(status);
      if (!status.running) {
        await loadAllData();
      }
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : "Failed to start folder sync"
      );
    }
  };

  const handleDeleteCandidate = async (id: string) => {
    await deleteCandidate(id);
    if (selectedCandidate?.id === id) setSelectedCandidate(null);
    setSelectedForCompare((prev) => prev.filter((x) => x !== id));
    await loadAllData();
  };

  const handleClearAll = async () => {
    await clearAllCandidates();
    setSelectedCandidate(null);
    setSelectedForCompare([]);
    await loadAllData();
  };

  const handleResetWorkspace = async () => {
    await resetWorkspace({ includeJds: true, includeSourceResumes: false });
    setSelectedCandidate(null);
    setSelectedForCompare([]);
    setSearchQuery("");
    setStatusFilter("all");
    setActiveJdId(null);
    setJdEvaluationsMap({});
    setJdSummary(null);
    await loadAllData(null);
  };

  const handleNavigateWithFilter = (tab: string, filterStatus?: string) => {
    setActiveTab(tab);
    if (filterStatus) setStatusFilter(filterStatus);
  };

  return (
    <div className="min-h-screen h-screen flex bg-slate-50 text-slate-900 overflow-hidden">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          setSelectedCandidate(null);
        }}
        totalCandidates={candidates.length}
        reviewCount={reviewQueue.length}
        compareCount={selectedForCompare.length}
        jdsCount={jds.length}
        systemStatus={systemStatus}
        isOffline={Boolean(loadError)}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          activeTab={activeTab}
          searchQuery={searchQuery}
          onSearchChange={(q) => {
            setSearchQuery(q);
            if (q && activeTab !== "candidates") setActiveTab("candidates");
          }}
          onSearchSubmit={() => setActiveTab("candidates")}
          onOpenUpload={() => setIsUploadOpen(true)}
          onResetWorkspace={handleResetWorkspace}
          onTriggerSync={handleTriggerSync}
          syncStatus={syncStatus}
          jds={jds}
          activeJdId={activeJdId}
          onSelectActiveJd={handleSelectActiveJd}
          isOffline={Boolean(loadError)}
        />

        {loadError && (
          <Card
            accent="rose"
            className="mx-6 mt-4 px-4 py-3 flex items-center justify-between gap-4 shrink-0"
          >
            <div className="flex items-center gap-2.5 text-xs text-rose-800">
              <AlertTriangle
                className="w-4 h-4 text-rose-600 shrink-0"
                strokeWidth={1.5}
              />
              <span>
                <strong className="font-semibold">
                  Backend API unavailable:
                </strong>{" "}
                {loadError}
              </span>
            </div>
            <Button
              variant="dangerSolid"
              size="xs"
              onClick={() => {
                setIsLoading(true);
                loadAllData();
              }}
              className="shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
              Retry
            </Button>
          </Card>
        )}

        <main className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="max-w-7xl mx-auto space-y-6 animate-pulse">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((n) => (
                  <div
                    key={n}
                    className="h-28 bg-white border border-slate-200/80 rounded-lg"
                  />
                ))}
              </div>
              <div className="h-80 bg-white border border-slate-200/80 rounded-lg" />
            </div>
          ) : (
            <div
              className={
                activeTab === "candidates" && selectedCandidate
                  ? "max-w-[1380px] mx-auto"
                  : "max-w-7xl mx-auto"
              }
            >
              {activeTab === "dashboard" && (
                <DashboardOverview
                  analytics={analytics}
                  candidates={hydratedCandidates}
                  reviewQueue={reviewQueue}
                  activeJd={activeJd}
                  jdSummary={jdSummary}
                  onSelectCandidate={async (c) => {
                    setActiveTab("candidates");
                    await handleSelectCandidate(c);
                  }}
                  onNavigate={handleNavigateWithFilter}
                  onOpenUpload={() => setIsUploadOpen(true)}
                />
              )}

              {activeTab === "jds" && (
                <JDWorkspaceView
                  jds={jds}
                  activeJdId={activeJdId}
                  onSelectActiveJd={handleSelectActiveJd}
                  onRefreshAll={() => loadAllData()}
                  onOpenCandidatePool={async (jdId) => {
                    await handleSelectActiveJd(jdId);
                    setActiveTab("candidates");
                  }}
                />
              )}

              {activeTab === "candidates" &&
                (selectedCandidate ? (
                  <CandidateDetailView
                    key={`${selectedCandidate.id}-${activeJdId ?? "base"}`}
                    candidate={selectedCandidate}
                    activeJd={activeJd}
                    onBack={() => setSelectedCandidate(null)}
                    onReviewSubmitted={async () => {
                      await loadAllData();
                      const refreshed = await fetchCandidateDetail(
                        selectedCandidate.id,
                        activeJdId
                      );
                      setSelectedCandidate(refreshed);
                    }}
                    onEvaluateForActiveJd={handleEvaluateSingleForActiveJd}
                    onCandidateUpdated={(updated) => setSelectedCandidate(updated)}
                    onDeleteCandidate={handleDeleteCandidate}
                    isSelectedForCompare={selectedForCompare.includes(
                      selectedCandidate.id
                    )}
                    onToggleCompare={() =>
                      handleToggleCompare(selectedCandidate.id)
                    }
                  />
                ) : (
                  <CandidateTable
                    candidates={hydratedCandidates}
                    activeJd={activeJd}
                    searchQuery={searchQuery}
                    onSearchChange={setSearchQuery}
                    statusFilter={statusFilter}
                    onStatusFilterChange={setStatusFilter}
                    onSelectCandidate={handleSelectCandidate}
                    selectedForCompare={selectedForCompare}
                    onToggleCompare={handleToggleCompare}
                    onOpenCompare={() => setActiveTab("compare")}
                    onDeleteCandidate={handleDeleteCandidate}
                    onClearAll={handleClearAll}
                  />
                ))}

              {activeTab === "review" && (
                <ReviewQueueView
                  queue={reviewQueue}
                  onReviewSubmitted={() => loadAllData()}
                  onInspectCandidate={async (c) => {
                    setActiveTab("candidates");
                    await handleSelectCandidate(c);
                  }}
                />
              )}

              {activeTab === "compare" && (
                <CandidateComparisonView
                  selectedIds={selectedForCompare}
                  allCandidates={hydratedCandidates}
                  rules={rulesConfig?.rules ?? []}
                  activeJd={activeJd}
                  onToggleCompare={handleToggleCompare}
                  onClearSelection={() => setSelectedForCompare([])}
                  onSelectCandidate={async (c) => {
                    setActiveTab("candidates");
                    await handleSelectCandidate(c);
                  }}
                />
              )}

              {activeTab === "analytics" && (
                <AnalyticsView
                  analytics={analytics}
                  candidates={hydratedCandidates}
                />
              )}

              {activeTab === "settings" && (
                <SettingsView onSettingsChanged={() => loadAllData()} />
              )}
            </div>
          )}
        </main>
      </div>

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadComplete={async (activatedJdId) => {
          if (activatedJdId) {
            setActiveJdId(activatedJdId);
            await loadAllData(activatedJdId);
          } else {
            await loadAllData();
          }
        }}
        jds={jds}
        activeJdId={activeJdId}
      />
    </div>
  );
}
