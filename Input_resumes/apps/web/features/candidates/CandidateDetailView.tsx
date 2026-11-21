'use client';

import React, { useState } from 'react';
import { 
  ArrowLeft, GraduationCap, Building2, BookOpen, FileText, 
  CheckCircle2, AlertTriangle, XCircle, ShieldCheck, Mail, Phone, 
  MapPin, ExternalLink, Download, Sparkles, MessageSquare, ThumbsUp, ThumbsDown
} from 'lucide-react';
import { Candidate, RuleEvaluation } from '../../types/candidate';

interface CandidateDetailViewProps {
  candidate: Candidate;
  onBack: () => void;
  onSubmitReview: (candidateId: string, verdict: string, notes?: string) => void;
}

export const CandidateDetailView: React.FC<CandidateDetailViewProps> = ({
  candidate,
  onBack,
  onSubmitReview
}) => {
  const [activeCenterTab, setActiveCenterTab] = useState<'education' | 'experience' | 'research' | 'markdown' | 'preview'>('education');
  const [reviewVerdict, setReviewVerdict] = useState<'approved' | 'rejected' | null>(null);
  const [reviewNotes, setReviewNotes] = useState(candidate.review_notes || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleReviewAction = async (verdict: 'approved' | 'rejected') => {
    setIsSubmitting(true);
    await onSubmitReview(candidate.id, verdict, reviewNotes);
    setReviewVerdict(verdict);
    setIsSubmitting(false);
  };

  return (
    <div className="space-y-4">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-2.5 shadow-xs">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Library</span>
        </button>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 font-mono">ID: {candidate.candidate_id}</span>
          <div className="h-4 w-px bg-slate-200"></div>
          {candidate.eligibility_status === 'eligible' ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" /> Eligible
            </span>
          ) : candidate.eligibility_status === 'needs_review' ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
              <AlertTriangle className="w-3.5 h-3.5" /> Needs Review
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200">
              <XCircle className="w-3.5 h-3.5" /> Disqualified
            </span>
          )}
        </div>
      </div>

      {/* Tri-Pane Architecture */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* LEFT PANE: Identity & Quick Stats (3 Cols) */}
        <div className="lg:col-span-3 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <div>
              <div className="w-12 h-12 rounded-xl bg-blue-900 text-white flex items-center justify-center font-bold text-lg shadow-xs mb-3">
                {candidate.name.split(' ').map(n => n[0]).slice(0, 2).join('')}
              </div>
              <h2 className="text-base font-bold text-slate-900">{candidate.name}</h2>
              <p className="text-xs text-blue-900 font-medium mt-0.5">{candidate.current_designation || 'Academic Researcher'}</p>
            </div>

            <div className="pt-3 border-t border-slate-100 space-y-2 text-xs text-slate-600">
              {candidate.email && (
                <div className="flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="truncate">{candidate.email}</span>
                </div>
              )}
              {candidate.phone && (
                <div className="flex items-center gap-2">
                  <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span>{candidate.phone}</span>
                </div>
              )}
              {candidate.location && (
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span>{candidate.location}</span>
                </div>
              )}
            </div>

            {candidate.summary && (
              <div className="pt-3 border-t border-slate-100">
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Summary</p>
                <p className="text-xs text-slate-600 leading-relaxed">{candidate.summary}</p>
              </div>
            )}

            {/* Quick Experience Stats Box */}
            <div className="pt-3 border-t border-slate-100 space-y-2">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Experience Breakdown</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 bg-slate-50 border border-slate-200 rounded">
                  <span className="text-[10px] text-slate-500 uppercase">Teaching</span>
                  <p className="font-mono font-bold text-slate-900 text-sm">{candidate.teaching_years} yrs</p>
                </div>
                <div className="p-2 bg-slate-50 border border-slate-200 rounded">
                  <span className="text-[10px] text-slate-500 uppercase">Research</span>
                  <p className="font-mono font-bold text-slate-900 text-sm">{candidate.research_years} yrs</p>
                </div>
                <div className="p-2 bg-slate-50 border border-slate-200 rounded">
                  <span className="text-[10px] text-slate-500 uppercase">Industry</span>
                  <p className="font-mono font-bold text-slate-900 text-sm">{candidate.industry_years} yrs</p>
                </div>
                <div className="p-2 bg-slate-50 border border-slate-200 rounded">
                  <span className="text-[10px] text-slate-500 uppercase">Career Total</span>
                  <p className="font-mono font-bold text-slate-900 text-sm">{candidate.total_years} yrs</p>
                </div>
              </div>
            </div>

            {/* Source Document Reference */}
            <div className="pt-3 border-t border-slate-100">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Source Resume</p>
              <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-800 truncate">
                  <FileText className="w-3.5 h-3.5 text-blue-900 shrink-0" />
                  <span className="truncate">{candidate.file_name}</span>
                </div>
                <div className="mt-1 text-[10px] text-slate-500 font-mono">
                  Preserved in input directory
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* CENTER PANE: Extracted Content & Tabbed Views (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            {/* Tabs Header */}
            <div className="flex border-b border-slate-200 bg-slate-50 text-xs font-medium">
              <button
                onClick={() => setActiveCenterTab('education')}
                className={`flex items-center gap-1.5 px-3.5 py-2.5 border-b-2 cursor-pointer transition-colors ${activeCenterTab === 'education' ? 'border-blue-900 text-blue-900 bg-white font-semibold' : 'border-transparent text-slate-600 hover:text-slate-900'}`}
              >
                <GraduationCap className="w-3.5 h-3.5" />
                <span>Education ({candidate.education?.length || 0})</span>
              </button>
              <button
                onClick={() => setActiveCenterTab('experience')}
                className={`flex items-center gap-1.5 px-3.5 py-2.5 border-b-2 cursor-pointer transition-colors ${activeCenterTab === 'experience' ? 'border-blue-900 text-blue-900 bg-white font-semibold' : 'border-transparent text-slate-600 hover:text-slate-900'}`}
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>Experience ({candidate.employment?.length || 0})</span>
              </button>
              <button
                onClick={() => setActiveCenterTab('research')}
                className={`flex items-center gap-1.5 px-3.5 py-2.5 border-b-2 cursor-pointer transition-colors ${activeCenterTab === 'research' ? 'border-blue-900 text-blue-900 bg-white font-semibold' : 'border-transparent text-slate-600 hover:text-slate-900'}`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Scholarship ({candidate.publications?.length || 0})</span>
              </button>
              <button
                onClick={() => setActiveCenterTab('markdown')}
                className={`flex items-center gap-1.5 px-3.5 py-2.5 border-b-2 cursor-pointer transition-colors ${activeCenterTab === 'markdown' ? 'border-blue-900 text-blue-900 bg-white font-semibold' : 'border-transparent text-slate-600 hover:text-slate-900'}`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Markdown</span>
              </button>
            </div>

            {/* Tab Contents */}
            <div className="p-5 max-h-[700px] overflow-y-auto space-y-4">
              {/* Education Tab */}
              {activeCenterTab === 'education' && (
                <div className="space-y-4">
                  {candidate.education && candidate.education.length > 0 ? (
                    candidate.education.map((edu, idx) => (
                      <div key={idx} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="text-xs font-bold text-slate-900">{edu.degree}</h4>
                            <p className="text-xs text-slate-600 mt-0.5">{edu.institution_normalized || edu.institution}</p>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800">
                            {edu.normalized_degree}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
                          {edu.graduation_year && <span className="font-mono">Year: {edu.graduation_year}</span>}
                          {edu.institution_category && (
                            <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">
                              {edu.institution_category} ({edu.institution_tier || 'Unclassified'})
                            </span>
                          )}
                          <span className="text-emerald-700 font-mono">Confidence: {intPct(edu.confidence)}</span>
                        </div>

                        {edu.evidence && (
                          <div className="p-2 bg-white rounded border border-slate-200 text-[11px] text-slate-600 italic">
                            <span className="font-bold text-slate-400 not-italic mr-1">Source Quote:</span>
                            "{edu.evidence}"
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-xs text-slate-400">No education records found.</div>
                  )}
                </div>
              )}

              {/* Experience Tab */}
              {activeCenterTab === 'experience' && (
                <div className="space-y-3">
                  {candidate.employment && candidate.employment.length > 0 ? (
                    candidate.employment.map((emp, idx) => (
                      <div key={idx} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1.5">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="text-xs font-bold text-slate-900">{emp.title}</h4>
                            <p className="text-xs text-slate-600">{emp.organization}</p>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${emp.category === 'teaching' ? 'bg-indigo-100 text-indigo-800' : emp.category === 'research' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-800'}`}>
                            {emp.category}
                          </span>
                        </div>

                        <div className="text-[11px] text-slate-500 font-mono">
                          {emp.start_date || 'N/A'} – {emp.end_date || 'Present'} ({emp.duration_years} yrs)
                        </div>

                        {emp.description && (
                          <p className="text-xs text-slate-600 mt-1 leading-relaxed">{emp.description}</p>
                        )}

                        {emp.evidence && (
                          <div className="p-2 bg-white rounded border border-slate-200 text-[11px] text-slate-500 italic mt-1">
                            "{emp.evidence}"
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-xs text-slate-400">No employment records found.</div>
                  )}
                </div>
              )}

              {/* Research Tab */}
              {activeCenterTab === 'research' && (
                <div className="space-y-3">
                  {candidate.publications && candidate.publications.length > 0 ? (
                    candidate.publications.map((pub, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1">
                        <h4 className="text-xs font-bold text-slate-900">{pub.title}</h4>
                        <div className="flex items-center gap-2 text-[11px] text-slate-600">
                          {pub.venue && <span className="italic">{pub.venue}</span>}
                          {pub.year && <span className="font-mono">({pub.year})</span>}
                          {pub.indexed && (
                            <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 text-[10px] font-semibold">
                              {pub.indexed}
                            </span>
                          )}
                        </div>
                        {pub.doi && (
                          <div className="text-[11px] font-mono text-blue-700">
                            DOI: {pub.doi}
                          </div>
                        )}
                        {pub.evidence && (
                          <div className="p-2 bg-white rounded border border-slate-200 text-[11px] text-slate-500 italic">
                            "{pub.evidence}"
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-xs text-slate-400">No publication records found.</div>
                  )}
                </div>
              )}

              {/* Markdown Tab */}
              {activeCenterTab === 'markdown' && (
                <div className="p-4 bg-slate-900 text-slate-200 rounded-lg font-mono text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {`# ${candidate.name}
**${candidate.current_designation || 'Academic Profile'}**

## Education
${candidate.education?.map(e => `- **${e.degree}** (${e.normalized_degree})\n  Institution: ${e.institution_normalized || e.institution} [${e.institution_category}]\n  Evidence: "${e.evidence || ''}"`).join('\n\n')}

## Experience
- Teaching: ${candidate.teaching_years} years
- Research: ${candidate.research_years} years
- Industry: ${candidate.industry_years} years
- Total: ${candidate.total_years} years

## Publications (${candidate.publications_count})
${candidate.publications?.map((p, i) => `${i+1}. ${p.title} - ${p.venue || ''} (${p.year || ''}) [${p.indexed || 'Peer-Reviewed'}]`).join('\n')}`}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT PANE: AI Screening & Traceable Evidence Panel (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            {/* Score & Confidence Header */}
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-800">Screening Evaluation</span>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-900 border border-blue-200">
                  Passing: 70.0%
                </span>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold font-mono text-slate-900">{candidate.overall_score}%</div>
                  <div className="text-[11px] text-slate-500">Overall Weighted Score</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold font-mono text-emerald-600">{intPct(candidate.confidence)}</div>
                  <div className="text-[11px] text-slate-500">Fact Extraction Confidence</div>
                </div>
              </div>
            </div>

            {/* Individual Screening Rules */}
            <div className="space-y-2.5 pt-2">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Rule-By-Rule Traceability</p>
              {candidate.rules_evaluated && candidate.rules_evaluated.length > 0 ? (
                candidate.rules_evaluated.map((rule) => (
                  <div 
                    key={rule.rule_id} 
                    className={`p-3 rounded-lg border text-xs space-y-1 ${rule.status === 'pass' ? 'bg-emerald-50/50 border-emerald-200' : 'bg-red-50/50 border-red-200'}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-semibold text-slate-900">
                        {rule.status === 'pass' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-red-600 shrink-0" />
                        )}
                        <span>{rule.name}</span>
                      </div>
                      <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${rule.is_mandatory ? 'bg-slate-200 text-slate-800' : 'bg-slate-100 text-slate-600'}`}>
                        {rule.is_mandatory ? 'Mandatory' : 'Preferred'} ({rule.weight}%)
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 leading-snug">{rule.reason}</p>

                    {rule.evidence && (
                      <div className="text-[10px] font-mono text-slate-500 bg-white/80 p-1.5 rounded border border-slate-200 truncate">
                        Quote: {rule.evidence}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-400">No rule evaluations available.</div>
              )}
            </div>

            {/* Recruiter Review Action Box */}
            <div className="pt-4 border-t border-slate-200 space-y-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-800">Recruiter Curation Verdict</p>
              
              <div>
                <label className="block text-[11px] text-slate-500 mb-1">Audit Notes / Comments</label>
                <textarea
                  rows={2}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Add evaluation comments for hiring committee..."
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-700"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleReviewAction('approved')}
                  disabled={isSubmitting}
                  className="flex items-center justify-center gap-1.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer transition-colors disabled:opacity-50"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  <span>Mark Eligible</span>
                </button>
                <button
                  onClick={() => handleReviewAction('rejected')}
                  disabled={isSubmitting}
                  className="flex items-center justify-center gap-1.5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer transition-colors disabled:opacity-50"
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                  <span>Disqualify</span>
                </button>
              </div>

              {reviewVerdict && (
                <div className="p-2 bg-slate-100 border border-slate-200 rounded text-center text-xs text-slate-700 font-semibold">
                  Verdict recorded: Candidate marked as {reviewVerdict.toUpperCase()}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

function intPct(val: number): string {
  return `${Math.round(val * 100)}%`;
}
