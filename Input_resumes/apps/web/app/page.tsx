'use client';

import React, { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { Sidebar, ScreenTab } from '../components/Sidebar';
import { DashboardOverview } from '../features/dashboard/DashboardOverview';
import { CandidateTable } from '../features/candidates/CandidateTable';
import { CandidateDetailView } from '../features/candidates/CandidateDetailView';
import { ReviewQueueView } from '../features/screening/ReviewQueueView';
import { CandidateComparisonView } from '../features/comparison/CandidateComparisonView';
import { AnalyticsView } from '../features/analytics/AnalyticsView';
import { SettingsView } from '../features/settings/SettingsView';
import { UploadModal } from '../components/UploadModal';

import { Candidate, AnalyticsOverview } from '../types/candidate';
import { 
  fetchCandidates, 
  fetchAnalytics, 
  fetchReviewQueue, 
  submitReview, 
  processAllResumes,
  deleteCandidate,
  clearAllCandidates
} from '../lib/api';

const EMPTY_ANALYTICS: AnalyticsOverview = {
  metrics: {
    total_resumes: 0,
    processed: 0,
    eligible: 0,
    needs_review: 0,
    disqualified: 0,
    average_teaching_years: 0,
    average_processing_time_sec: 0
  },
  distributions: {
    degree: [],
    institution_category: [],
    experience: []
  },
  telemetry: {
    deterministic_resolutions: 0,
    jev_decision_calls: 0,
    groq_api_calls: 0,
    escalations: 0,
    total_latency_ms: 0
  }
};

export default function Home() {
  const [activeTab, setActiveTab] = useState<ScreenTab>('overview');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview>(EMPTY_ANALYTICS);
  const [reviewQueue, setReviewQueue] = useState<Candidate[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [compareCandidateIds, setCompareCandidateIds] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [globalSearchTerm, setGlobalSearchTerm] = useState('');

  // Initial Data Fetch
  const loadData = async () => {
    try {
      const candData = await fetchCandidates();
      setCandidates(candData.candidates);

      const analyticsData = await fetchAnalytics();
      setAnalytics(analyticsData);

      const queueData = await fetchReviewQueue();
      setReviewQueue(queueData);
    } catch (e) {
      console.warn('Using mock data default:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectCandidate = (candidateId: string) => {
    setSelectedCandidateId(candidateId);
    setActiveTab('detail');
  };

  const handleCompareCandidates = (candidateIds: string[]) => {
    setCompareCandidateIds(candidateIds);
    setActiveTab('compare');
  };

  const handleReviewSubmit = async (candidateId: string, verdict: string, notes?: string) => {
    await submitReview(candidateId, verdict, notes);
    // Optimistic local update
    setCandidates((prev) =>
      prev.map((c) =>
        c.id === candidateId
          ? {
              ...c,
              eligibility_status: verdict === 'approved' ? 'eligible' : 'disqualified',
              review_status: 'Manually verified',
              review_notes: notes || c.review_notes
            }
          : c
      )
    );
    setReviewQueue((prev) => prev.filter((c) => c.id !== candidateId));
  };

  const handleSyncResumes = async () => {
    setIsProcessing(true);
    await processAllResumes();
    setTimeout(async () => {
      await loadData();
      setIsProcessing(false);
    }, 2000);
  };

  const handleDeleteCandidate = async (candidateId: string) => {
    const ok = await deleteCandidate(candidateId);
    if (ok) {
      setCandidates((prev) => prev.filter((c) => c.id !== candidateId && c.candidate_id !== candidateId));
      setReviewQueue((prev) => prev.filter((c) => c.id !== candidateId && c.candidate_id !== candidateId));
      try {
        const analyticsData = await fetchAnalytics();
        setAnalytics(analyticsData);
      } catch (e) {}
    }
  };

  const handleClearAll = async () => {
    if (confirm("Are you sure you want to delete and clear ALL candidate profiles and screening data? (This will reset the platform without deleting your source files).")) {
      const ok = await clearAllCandidates();
      if (ok) {
        setCandidates([]);
        setReviewQueue([]);
        setSelectedCandidateId(null);
        setCompareCandidateIds([]);
        try {
          const analyticsData = await fetchAnalytics();
          setAnalytics(analyticsData);
        } catch (e) {}
      }
    }
  };

  const selectedCandidate = candidates.find(
    (c) => c.id === selectedCandidateId || c.candidate_id === selectedCandidateId
  ) || candidates[0];

  const candidatesForComparison = candidates.filter((c) =>
    compareCandidateIds.includes(c.id) || compareCandidateIds.includes(c.candidate_id)
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        onSearch={(term) => {
          setGlobalSearchTerm(term);
          if (term.trim() && activeTab !== 'library') {
            setActiveTab('library');
          }
        }}
        onRefresh={handleSyncResumes}
        onOpenUpload={() => setIsUploadModalOpen(true)}
        isProcessing={isProcessing}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          reviewQueueCount={reviewQueue.length}
          totalCandidatesCount={candidates.length}
        />

        <main className="flex-1 p-6 overflow-y-auto max-w-[1600px] mx-auto w-full">
          {activeTab === 'overview' && (
            <DashboardOverview
              analytics={analytics}
              recentCandidates={candidates}
              onSelectCandidate={handleSelectCandidate}
              onNavigateToTab={setActiveTab}
            />
          )}

          {activeTab === 'library' && (
            <CandidateTable
              candidates={candidates}
              onSelectCandidate={handleSelectCandidate}
              onCompareCandidates={handleCompareCandidates}
              onOpenUploadModal={() => setIsUploadModalOpen(true)}
              onDeleteCandidate={handleDeleteCandidate}
              onClearAll={handleClearAll}
            />
          )}

          {activeTab === 'detail' && selectedCandidate && (
            <CandidateDetailView
              candidate={selectedCandidate}
              onBack={() => setActiveTab('library')}
              onSubmitReview={handleReviewSubmit}
            />
          )}

          {activeTab === 'queue' && (
            <ReviewQueueView
              queueCandidates={reviewQueue}
              onSelectCandidate={handleSelectCandidate}
              onSubmitReview={handleReviewSubmit}
            />
          )}

          {activeTab === 'compare' && (
            <CandidateComparisonView
              candidates={candidatesForComparison.length > 0 ? candidatesForComparison : candidates.slice(0, 3)}
              onBack={() => setActiveTab('library')}
              onSelectCandidate={handleSelectCandidate}
            />
          )}

          {activeTab === 'analytics' && (
            <AnalyticsView analytics={analytics} />
          )}

          {activeTab === 'settings' && (
            <SettingsView />
          )}
        </main>
      </div>

      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={async () => {
          await loadData();
          setActiveTab('library');
        }}
      />
    </div>
  );
}
