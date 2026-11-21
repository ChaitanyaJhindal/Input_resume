'use client';

import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, XCircle, Eye, ThumbsUp, ThumbsDown, ShieldAlert } from 'lucide-react';
import { Candidate } from '../../types/candidate';

interface ReviewQueueViewProps {
  queueCandidates: Candidate[];
  onSelectCandidate: (candidateId: string) => void;
  onSubmitReview: (candidateId: string, verdict: string) => void;
}

export const ReviewQueueView: React.FC<ReviewQueueViewProps> = ({
  queueCandidates,
  onSelectCandidate,
  onSubmitReview
}) => {
  const [resolvedIds, setResolvedIds] = useState<{ [id: string]: string }>({});

  const handleAction = async (id: string, verdict: 'approved' | 'rejected') => {
    await onSubmitReview(id, verdict);
    setResolvedIds(prev => ({ ...prev, [id]: verdict }));
  };

  return (
    <div className="space-y-4">
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">Recruiter Human Review Queue</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
              {queueCandidates.length} Pending Audit
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Cases flagged due to borderline confidence scores, unclassified institutions, or mandatory requirement conflicts.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {queueCandidates.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <h3 className="text-sm font-bold text-slate-800">Review Queue Cleared</h3>
            <p className="text-xs text-slate-400">All current candidates have been processed with high confidence or verified.</p>
          </div>
        ) : (
          queueCandidates.map((cand) => {
            const isResolved = resolvedIds[cand.id];

            return (
              <div 
                key={cand.id} 
                className={`bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all ${isResolved ? 'opacity-50 bg-slate-50' : ''}`}
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-sm font-bold text-slate-900 hover:text-blue-900 cursor-pointer" onClick={() => onSelectCandidate(cand.id)}>
                      {cand.name}
                    </h3>
                    <span className="text-[11px] font-mono text-slate-400">{cand.file_name}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-900 border border-blue-200">
                      Score: {cand.overall_score}%
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    <span className="font-medium text-slate-800">{cand.highest_degree || 'Unspecified'}</span>
                    <span className="text-slate-300">•</span>
                    <span>{cand.highest_institution || 'Institution Unspecified'}</span>
                    <span className="text-slate-300">•</span>
                    <span>{cand.teaching_years} yrs teaching</span>
                  </div>

                  {/* Flagged Reasons Callout */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1">
                      <ShieldAlert className="w-3 h-3 text-amber-600" /> Review Triggers:
                    </span>
                    {cand.rules_evaluated
                      ?.filter(r => r.status === 'fail' && r.is_mandatory)
                      .map(r => (
                        <span key={r.rule_id} className="px-2 py-0.5 rounded bg-red-50 text-red-700 text-[10px] font-medium border border-red-200">
                          {r.name} Failed
                        </span>
                      ))}
                    {cand.confidence < 0.85 && (
                      <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-medium border border-amber-200">
                        Low Confidence ({Math.round(cand.confidence * 100)}%)
                      </span>
                    )}
                    {(!cand.highest_degree || cand.highest_degree === 'Other') && (
                      <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-medium border border-amber-200">
                        Degree Level Unclassified
                      </span>
                    )}
                  </div>
                </div>

                {/* Quick Action Buttons */}
                <div className="flex items-center gap-2 shrink-0">
                  {isResolved ? (
                    <span className="text-xs font-bold uppercase text-slate-500">
                      Marked as {isResolved}
                    </span>
                  ) : (
                    <>
                      <button
                        onClick={() => onSelectCandidate(cand.id)}
                        className="px-3 py-1.5 text-xs font-semibold text-blue-900 hover:bg-blue-50 border border-blue-200 rounded-md transition-colors cursor-pointer flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect Evidence</span>
                      </button>
                      <button
                        onClick={() => handleAction(cand.id, 'approved')}
                        className="px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md shadow-2xs transition-colors cursor-pointer flex items-center gap-1"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span>Approve</span>
                      </button>
                      <button
                        onClick={() => handleAction(cand.id, 'rejected')}
                        className="px-3 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-md shadow-2xs transition-colors cursor-pointer flex items-center gap-1"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                        <span>Disqualify</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
