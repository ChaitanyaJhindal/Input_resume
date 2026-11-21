'use client';

import React from 'react';
import { GitCompare, ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Eye } from 'lucide-react';
import { Candidate } from '../../types/candidate';

interface CandidateComparisonViewProps {
  candidates: Candidate[];
  onBack: () => void;
  onSelectCandidate: (candidateId: string) => void;
}

export const CandidateComparisonView: React.FC<CandidateComparisonViewProps> = ({
  candidates,
  onBack,
  onSelectCandidate
}) => {
  if (!candidates || candidates.length < 2) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-3">
        <GitCompare className="w-8 h-8 text-slate-400 mx-auto" />
        <h3 className="text-sm font-bold text-slate-800">Select Candidates to Compare</h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          Please select 2 to 4 candidates from the Resume Library to view their side-by-side qualifications matrix.
        </p>
        <button
          onClick={onBack}
          className="mt-2 px-3.5 py-1.5 bg-blue-900 text-white rounded-md text-xs font-semibold hover:bg-blue-800 transition-colors cursor-pointer"
        >
          Go to Resume Library
        </button>
      </div>
    );
  }

  const comparisonAttributes = [
    { label: 'Highest Degree', key: 'highest_degree' },
    { label: 'Degree Institution', key: 'highest_institution' },
    { label: 'Institution Category', key: 'highest_institution_category' },
    { label: 'Institution Tier', key: 'institution_tier' },
    { label: 'Teaching Experience', format: (c: Candidate) => `${c.teaching_years} years` },
    { label: 'Research Experience', format: (c: Candidate) => `${c.research_years} years` },
    { label: 'Industry Experience', format: (c: Candidate) => `${c.industry_years} years` },
    { label: 'Career Total', format: (c: Candidate) => `${c.total_years} years` },
    { label: 'Publications Count', format: (c: Candidate) => `${c.publications_count} papers` },
    { label: 'Screening Score', format: (c: Candidate) => `${c.overall_score}%` },
    { label: 'Extraction Confidence', format: (c: Candidate) => `${Math.round(c.confidence * 100)}%` },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Library</span>
        </button>
        <div className="text-xs text-slate-500">
          Comparing <span className="font-bold text-slate-800">{candidates.length}</span> candidates side-by-side
        </div>
      </div>

      {/* Comparison Grid Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="py-4 px-4 w-48 text-slate-500 font-bold uppercase tracking-wider text-[11px] bg-slate-100/50">
                Candidate Profile
              </th>
              {candidates.map((cand) => (
                <th key={cand.id} className="py-4 px-4 min-w-[220px] align-top">
                  <div className="font-bold text-sm text-slate-900">{cand.name}</div>
                  <div className="text-[11px] text-blue-900 font-medium">{cand.current_designation || 'Academic Profile'}</div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5 truncate">{cand.file_name}</div>
                  <button
                    onClick={() => onSelectCandidate(cand.id)}
                    className="mt-2 flex items-center gap-1 text-[11px] font-semibold text-blue-900 hover:underline cursor-pointer"
                  >
                    <Eye className="w-3 h-3" />
                    <span>Inspect Detail</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {/* Status Row */}
            <tr className="bg-slate-50/30">
              <td className="py-3 px-4 font-bold text-slate-700 bg-slate-100/50">
                Eligibility Status
              </td>
              {candidates.map((cand) => (
                <td key={cand.id} className="py-3 px-4">
                  {cand.eligibility_status === 'eligible' ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="w-3 h-3" /> Eligible
                    </span>
                  ) : cand.eligibility_status === 'needs_review' ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                      <AlertTriangle className="w-3 h-3" /> Needs Review
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200">
                      <XCircle className="w-3 h-3" /> Disqualified
                    </span>
                  )}
                </td>
              ))}
            </tr>

            {/* Structured Attributes */}
            {comparisonAttributes.map((attr) => (
              <tr key={attr.label} className="hover:bg-slate-50/50 transition-colors">
                <td className="py-2.5 px-4 font-medium text-slate-500 bg-slate-100/50">
                  {attr.label}
                </td>
                {candidates.map((cand) => (
                  <td key={cand.id} className="py-2.5 px-4 text-slate-800 font-semibold font-mono text-xs">
                    {attr.format ? attr.format(cand) : (cand as any)[attr.key!] || '-'}
                  </td>
                ))}
              </tr>
            ))}

            {/* Mandatory Screening Rules Matrix */}
            <tr className="bg-slate-100/80 font-bold text-slate-700">
              <td colSpan={candidates.length + 1} className="py-2 px-4 uppercase text-[10px] tracking-wider text-slate-500">
                Mandatory Screening Rules Evaluation
              </td>
            </tr>

            {['RULE_MIN_DEGREE', 'RULE_MIN_TEACHING_EXP', 'RULE_MIN_PUBLICATIONS'].map((ruleId) => {
              const ruleNames: { [k: string]: string } = {
                RULE_MIN_DEGREE: 'Doctoral Requirement',
                RULE_MIN_TEACHING_EXP: 'Min Teaching (>=2y)',
                RULE_MIN_PUBLICATIONS: 'Min Publications (>=2)'
              };

              return (
                <tr key={ruleId} className="hover:bg-slate-50/50">
                  <td className="py-2.5 px-4 font-medium text-slate-600 bg-slate-100/50">
                    {ruleNames[ruleId]}
                  </td>
                  {candidates.map((cand) => {
                    const evaluation = cand.rules_evaluated?.find(r => r.rule_id === ruleId);
                    const passed = evaluation?.status === 'pass';

                    return (
                      <td key={cand.id} className="py-2.5 px-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold ${passed ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                          {passed ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                          <span>{passed ? 'Passed' : 'Failed'}</span>
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
