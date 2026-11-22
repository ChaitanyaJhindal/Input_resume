"use client";

import React, { useEffect, useState } from "react";
import {
  ArrowLeft,
  ExternalLink,
  GitCompare,
  Trash2,
  RefreshCw,
  Loader2,
} from "lucide-react";
import {
  Candidate,
  JDApprovalStatus,
  JobDescription,
  ResumeResultResponse,
} from "../../types/candidate";
import {
  enrichCandidateLinks,
  fetchResumeResult,
  getResumeFileUrl,
  submitJDApproval,
  submitReviewVerdict,
} from "../../lib/api";
import { Button, UnderlineTabs } from "../../components/ui";
import { CandidateHeaderCard } from "./detail/CandidateHeaderCard";
import { OverviewInsightsTab } from "./detail/OverviewInsightsTab";
import { CareerPortfolioTab } from "./detail/CareerPortfolioTab";
import {
  EvidenceTab,
  ResearchTab,
  SourceTab,
} from "./detail/ResearchAndEvidenceTabs";

interface CandidateDetailViewProps {
  candidate: Candidate;
  activeJd: JobDescription | null;
  onBack: () => void;
  onReviewSubmitted: () => Promise<void>;
  onEvaluateForActiveJd: (candidateId: string) => Promise<void>;
  onCandidateUpdated: (updated: Candidate) => void;
  onDeleteCandidate: (id: string) => Promise<void>;
  isSelectedForCompare: boolean;
  onToggleCompare: () => void;
}

type DetailTab = "overview" | "career" | "research" | "evidence" | "source";

export const CandidateDetailView: React.FC<CandidateDetailViewProps> = ({
  candidate,
  activeJd,
  onBack,
  onReviewSubmitted,
  onEvaluateForActiveJd,
  onCandidateUpdated,
  onDeleteCandidate,
  isSelectedForCompare,
  onToggleCompare,
}) => {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [notes, setNotes] = useState(
    candidate.jd_evaluation?.approval_notes ?? candidate.review_notes ?? ""
  );
  const [isSavingReview, setIsSavingReview] = useState(false);
  const [isEnrichingLinks, setIsEnrichingLinks] = useState(false);
  const [isEvaluatingJd, setIsEvaluatingJd] = useState(false);
  const [reviewFeedback, setReviewFeedback] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [markdownResult, setMarkdownResult] =
    useState<ResumeResultResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadMarkdown() {
      const res = await fetchResumeResult(candidate.id);
      if (!cancelled) setMarkdownResult(res);
    }
    loadMarkdown();
    return () => {
      cancelled = true;
    };
  }, [candidate.id]);

  const handleVerdict = async (verdict: "approved" | "rejected") => {
    setIsSavingReview(true);
    setReviewFeedback(null);
    try {
      await submitReviewVerdict(candidate.id, verdict, notes);
      setReviewFeedback(
        verdict === "approved"
          ? "Saved baseline verdict: Candidate marked Eligible."
          : "Saved baseline verdict: Candidate marked Disqualified."
      );
      await onReviewSubmitted();
    } catch (err) {
      setReviewFeedback(
        err instanceof Error ? err.message : "Failed to save review verdict"
      );
    } finally {
      setIsSavingReview(false);
    }
  };

  const handleJdApproval = async (approvalStatus: JDApprovalStatus) => {
    if (!activeJd) return;
    setIsSavingReview(true);
    setReviewFeedback(null);
    try {
      await submitJDApproval(activeJd.jd_id, candidate.id, approvalStatus, notes);
      setReviewFeedback(
        `Saved JD decision (${approvalStatus.replace(/_/g, " ")}) for '${activeJd.title}'.`
      );
      await onReviewSubmitted();
    } catch (err) {
      setReviewFeedback(
        err instanceof Error ? err.message : "Failed to submit JD decision"
      );
    } finally {
      setIsSavingReview(false);
    }
  };

  const handleEnrichLinks = async () => {
    setIsEnrichingLinks(true);
    setReviewFeedback(null);
    try {
      const res = await enrichCandidateLinks(candidate.id);
      if (res.candidate) {
        onCandidateUpdated({
          ...res.candidate,
          jd_evaluation: candidate.jd_evaluation,
        });
      }
      setReviewFeedback(
        res.external_verification?.citation_count !== null &&
          res.external_verification?.citation_count !== undefined
          ? `Verified via ${res.external_verification.match_method}: ${res.external_verification.citation_count} citations, h-index ${res.external_verification.h_index ?? 0}.`
          : `Scanned CV links (${res.academic_links.length} profile links detected).`
      );
    } catch (err) {
      setReviewFeedback(
        err instanceof Error ? err.message : "Link verification failed"
      );
    } finally {
      setIsEnrichingLinks(false);
    }
  };

  const fileUrl = getResumeFileUrl(candidate.id);
  const isPdf = candidate.file_name.toLowerCase().endsWith(".pdf");
  const publications =
    candidate.research?.publications?.length
      ? candidate.research.publications
      : candidate.publications ?? [];
  const researchProjects = candidate.research?.research_projects ?? [];
  const researchDomains = candidate.research?.research_domains ?? [];
  const coursesTaught = candidate.courses_taught ?? [];
  const highlights =
    candidate.jd_evaluation?.standout_highlights?.length
      ? candidate.jd_evaluation.standout_highlights
      : candidate.notable_highlights ?? [];
  const jdEval = candidate.jd_evaluation;

  const groundingPct =
    candidate.grounding_score !== null && candidate.grounding_score !== undefined
      ? Math.round(candidate.grounding_score * 100)
      : candidate.metadata?.grounding_score !== undefined
      ? Math.round(candidate.metadata.grounding_score * 100)
      : null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-navy-900 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" strokeWidth={1.5} />
          Back to Candidate Pool
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleEnrichLinks}
            disabled={isEnrichingLinks}
          >
            {isEnrichingLinks ? (
              <Loader2
                className="w-3.5 h-3.5 animate-spin text-navy-900"
                strokeWidth={1.5}
              />
            ) : (
              <RefreshCw
                className="w-3.5 h-3.5 text-slate-500"
                strokeWidth={1.5}
              />
            )}
            Verify Academic Links
          </Button>

          <Button
            variant={isSelectedForCompare ? "navySubtle" : "secondary"}
            size="sm"
            onClick={onToggleCompare}
          >
            <GitCompare className="w-3.5 h-3.5" strokeWidth={1.5} />
            {isSelectedForCompare ? "In Comparison" : "Add to Compare"}
          </Button>

          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-slate-200/80 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition"
          >
            <ExternalLink className="w-3.5 h-3.5" strokeWidth={1.5} />
            Open Raw CV
          </a>

          {confirmDelete ? (
            <div className="inline-flex items-center gap-1.5">
              <Button
                variant="dangerSolid"
                size="sm"
                onClick={() => onDeleteCandidate(candidate.id)}
              >
                Confirm Delete
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="danger"
              size="sm"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
              Delete
            </Button>
          )}
        </div>
      </div>

      <CandidateHeaderCard
        candidate={candidate}
        activeJd={activeJd}
        jdEval={jdEval}
        groundingPct={groundingPct}
        notes={notes}
        onNotesChange={setNotes}
        isSavingReview={isSavingReview}
        reviewFeedback={reviewFeedback}
        onVerdict={handleVerdict}
        onJdApproval={handleJdApproval}
      />

      <UnderlineTabs
        activeId={activeTab}
        onChange={setActiveTab}
        items={[
          {
            id: "overview",
            label: activeJd ? "JD Insights & Screening" : "Screening & Rules",
          },
          {
            id: "career",
            label: "Degrees, Courses & Career",
            count: coursesTaught.length,
          },
          {
            id: "research",
            label: "Research & Grants",
            count: publications.length,
          },
          { id: "evidence", label: "Evidence & Telemetry" },
          { id: "source", label: "Source CV & Markdown" },
        ]}
      />

      {activeTab === "overview" && (
        <OverviewInsightsTab
          candidate={candidate}
          activeJd={activeJd}
          jdEval={jdEval}
          highlights={highlights}
          isEvaluatingJd={isEvaluatingJd}
          onEvaluateJd={async () => {
            setIsEvaluatingJd(true);
            try {
              await onEvaluateForActiveJd(candidate.id);
            } finally {
              setIsEvaluatingJd(false);
            }
          }}
        />
      )}

      {activeTab === "career" && <CareerPortfolioTab candidate={candidate} />}

      {activeTab === "research" && (
        <ResearchTab
          researchDomains={researchDomains}
          publications={publications}
          researchProjects={researchProjects}
        />
      )}

      {activeTab === "evidence" && <EvidenceTab candidate={candidate} />}

      {activeTab === "source" && (
        <SourceTab
          candidate={candidate}
          fileUrl={fileUrl}
          isPdf={isPdf}
          markdownResult={markdownResult}
        />
      )}
    </div>
  );
};
