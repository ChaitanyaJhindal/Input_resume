"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Eye,
  ShieldAlert,
} from "lucide-react";
import { Candidate } from "../../types/candidate";
import { submitReviewVerdict } from "../../lib/api";
import { Button, Card, EmptyState, StatusPill } from "../../components/ui";

interface ReviewQueueViewProps {
  queue: Candidate[];
  onReviewSubmitted: () => Promise<void>;
  onInspectCandidate: (candidate: Candidate) => void;
}

export const ReviewQueueView: React.FC<ReviewQueueViewProps> = ({
  queue,
  onReviewSubmitted,
  onInspectCandidate,
}) => {
  const [notesById, setNotesById] = useState<Record<string, string>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleDecision = async (
    candidateId: string,
    verdict: "approved" | "rejected"
  ) => {
    setSubmittingId(candidateId);
    setErrorMsg(null);
    try {
      await submitReviewVerdict(
        candidateId,
        verdict,
        notesById[candidateId] || undefined
      );
      await onReviewSubmitted();
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to submit decision"
      );
    } finally {
      setSubmittingId(null);
    }
  };

  if (queue.length === 0) {
    return (
      <EmptyState
        icon={
          <CheckCircle2
            className="w-5 h-5 text-emerald-600"
            strokeWidth={1.5}
          />
        }
        title="No Pending Manual Reviews"
        description="Every candidate in the database meets automated confidence and source grounding thresholds, or has already been manually adjudicated."
      />
    );
  }

  return (
    <div className="space-y-4">
      <Card className="p-4 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-slate-900">
            Candidates Flagged for Human Verification (
            <span className="font-mono tabular-nums">{queue.length}</span>)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Sorted ascending by extraction confidence. Submitted verdicts persist
            to SQLite and disk snapshots.
          </p>
        </div>
      </Card>

      {errorMsg && (
        <Card
          accent="rose"
          className="p-3 text-xs text-rose-800 flex items-center gap-2"
        >
          <AlertCircle
            className="w-4 h-4 text-rose-600 shrink-0"
            strokeWidth={1.5}
          />
          <span>{errorMsg}</span>
        </Card>
      )}

      <div className="space-y-4">
        {queue.map((cand) => {
          const isBusy = submittingId === cand.id;
          return (
            <Card key={cand.id} className="p-5 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900">
                      {cand.name}
                    </h3>
                    <StatusPill variant="amber" mono>
                      {Math.round(cand.confidence * 100)}% Confidence
                    </StatusPill>
                    <span className="text-[11px] font-mono tabular-nums text-slate-500">
                      Score: {cand.overall_score.toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">
                    {cand.highest_degree} &bull; {cand.highest_institution} (
                    {cand.highest_institution_category}) &bull;{" "}
                    <span className="font-mono tabular-nums">
                      {cand.teaching_years} yrs
                    </span>{" "}
                    teaching &bull;{" "}
                    <span className="font-mono tabular-nums">
                      {cand.publications_count}
                    </span>{" "}
                    pubs
                  </p>
                </div>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onInspectCandidate(cand)}
                >
                  <Eye className="w-3.5 h-3.5" strokeWidth={1.5} />
                  Inspect Full CV
                </Button>
              </div>

              <div className="p-3.5 rounded-md bg-slate-50/70 border border-slate-200/80 border-l-2 border-l-amber-500 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-900">
                  <ShieldAlert
                    className="w-4 h-4 text-amber-600"
                    strokeWidth={1.5}
                  />
                  Review Triggers
                </div>
                <ul className="list-disc pl-5 text-xs text-slate-700 space-y-0.5">
                  {(cand.review_reasons ?? ["Routine confidence review"]).map(
                    (reason, idx) => (
                      <li key={idx}>{reason}</li>
                    )
                  )}
                </ul>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  value={notesById[cand.id] ?? ""}
                  onChange={(e) =>
                    setNotesById((prev) => ({
                      ...prev,
                      [cand.id]: e.target.value,
                    }))
                  }
                  placeholder="Verification note (e.g., confirmed degree transcript from PDF page 2)..."
                  className="flex-1 min-w-[240px] px-3 py-1.5 text-xs bg-slate-50/70 border border-slate-200/80 rounded-md focus:outline-none focus:bg-white focus:border-navy-900"
                />

                <Button
                  variant="primary"
                  size="sm"
                  disabled={isBusy}
                  onClick={() => handleDecision(cand.id, "approved")}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                  Approve Eligible
                </Button>

                <Button
                  variant="danger"
                  size="sm"
                  disabled={isBusy}
                  onClick={() => handleDecision(cand.id, "rejected")}
                >
                  <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                  Disqualify
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
