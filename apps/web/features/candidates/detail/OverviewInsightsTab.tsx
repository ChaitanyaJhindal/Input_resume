"use client";

import React from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Scale,
  Compass,
  HelpCircle,
} from "lucide-react";
import {
  Candidate,
  CandidateJDEvaluation,
  JobDescription,
  NotableHighlight,
} from "../../../types/candidate";
import {
  Button,
  Card,
  CardHeader,
  ProgressBar,
  StatusPill,
  requirementStatusVariant,
} from "../../../components/ui";

interface OverviewInsightsTabProps {
  candidate: Candidate;
  activeJd: JobDescription | null;
  jdEval: CandidateJDEvaluation | null | undefined;
  highlights: NotableHighlight[];
  isEvaluatingJd: boolean;
  onEvaluateJd: () => Promise<void>;
}

export const OverviewInsightsTab: React.FC<OverviewInsightsTabProps> = ({
  candidate,
  activeJd,
  jdEval,
  highlights,
  isEvaluatingJd,
  onEvaluateJd,
}) => {
  return (
    <div className="space-y-5">
      {activeJd && !jdEval && (
        <Card
          accent="navy"
          className="p-5 flex flex-wrap items-center justify-between gap-4"
        >
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Not yet evaluated against &ldquo;{activeJd.title}&rdquo;
            </h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Run dynamic JD evaluation to generate requirement fit, compensating strengths, and interview probes.
            </p>
          </div>
          <Button
            variant="primary"
            size="md"
            disabled={isEvaluatingJd}
            onClick={onEvaluateJd}
            className="shrink-0"
          >
            {isEvaluatingJd ? "Evaluating..." : "Evaluate for Active JD"}
          </Button>
        </Card>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        {/* Main Dossier Column */}
        <div className="xl:col-span-8 space-y-5">
          {jdEval && activeJd && (
            <>
              <Card className="p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <Scale
                        className="w-4 h-4 text-navy-900"
                        strokeWidth={1.5}
                      />
                      Holistic Assessment for &ldquo;{activeJd.title}&rdquo;
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Committee status:{" "}
                      <strong className="capitalize text-slate-700">
                        {jdEval.approval_status.replace(/_/g, " ")}
                      </strong>
                    </p>
                  </div>
                </div>

                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50/70 p-3.5 rounded-md border border-slate-200/80">
                  {jdEval.executive_brief}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 text-xs">
                  {(
                    [
                      {
                        label: "Requirements",
                        val: jdEval.dimension_scores.requirement_fit,
                      },
                      {
                        label: "Domain Fit",
                        val: jdEval.dimension_scores.domain_semantic_fit,
                      },
                      {
                        label: "Teaching",
                        val: jdEval.dimension_scores.teaching_fit,
                      },
                      {
                        label: "Research",
                        val: jdEval.dimension_scores.research_and_impact,
                      },
                      {
                        label: "Alt Strengths",
                        val: jdEval.dimension_scores.alternative_strength_credit,
                      },
                    ] as const
                  ).map((d) => (
                    <div
                      key={d.label}
                      className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80"
                    >
                      <div className="flex justify-between text-slate-600 mb-1.5 gap-1">
                        <span className="truncate">{d.label}</span>
                        <span className="font-mono tabular-nums font-bold text-slate-900">
                          {d.val.toFixed(0)}%
                        </span>
                      </div>
                      <ProgressBar
                        value={d.val}
                        max={100}
                        minVisiblePct={2}
                        variant="navy"
                      />
                    </div>
                  ))}
                </div>
              </Card>

              {jdEval.compensating_strengths.length > 0 && (
                <Card accent="navy" className="p-5 space-y-3">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Compass
                      className="w-4 h-4 text-navy-900"
                      strokeWidth={1.5}
                    />
                    Compensating Strengths &amp; Equivalence Rationale
                  </h3>
                  <div className="space-y-2.5">
                    {jdEval.compensating_strengths.map((cs, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-md bg-slate-50/60 border border-slate-200/80 text-xs space-y-1"
                      >
                        <div className="font-semibold text-slate-900">
                          Gap: {cs.missed_requirement}
                        </div>
                        <div className="text-navy-900 font-medium">
                          Offset by: {cs.compensating_evidence}
                        </div>
                        <p className="text-slate-600 leading-relaxed">
                          {cs.rationale}
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              <Card className="overflow-hidden">
                <CardHeader>
                  <h3 className="text-sm font-bold text-slate-900">
                    JD Requirement-by-Requirement Matrix (
                    <span className="font-mono tabular-nums">
                      {jdEval.requirement_matrix.length}
                    </span>
                    )
                  </h3>
                </CardHeader>
                <div className="divide-y divide-slate-200/60">
                  {jdEval.requirement_matrix.map((rm) => (
                    <div
                      key={rm.requirement_id}
                      className="p-4 flex items-start justify-between gap-4 text-xs"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusPill
                            variant={requirementStatusVariant(rm.status)}
                            className="text-[10px] font-bold uppercase"
                          >
                            {rm.status.replace("_", " ")}
                          </StatusPill>
                          <span className="font-bold text-slate-900">
                            {rm.label}
                          </span>
                        </div>
                        <p className="text-slate-600">{rm.rationale}</p>
                        {rm.evidence && (
                          <p className="text-[11px] text-slate-500 italic">
                            CV Evidence: &ldquo;{rm.evidence}&rdquo;
                          </p>
                        )}
                      </div>
                      <span className="font-mono tabular-nums font-semibold text-slate-800 shrink-0">
                        {rm.score.toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}

          <Card className="overflow-hidden">
            <CardHeader>
              <h3 className="text-sm font-bold text-slate-900">
                Baseline Screening Rules (
                <span className="font-mono tabular-nums">
                  {candidate.rules_evaluated.length}
                </span>
                )
              </h3>
            </CardHeader>
            <div className="divide-y divide-slate-200/60">
              {candidate.rules_evaluated.map((rule) => (
                <div
                  key={rule.rule_id}
                  className="p-4 flex items-start justify-between gap-4"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {rule.status === "pass" ? (
                        <CheckCircle2
                          className="w-4 h-4 text-emerald-600 shrink-0"
                          strokeWidth={1.5}
                        />
                      ) : (
                        <XCircle
                          className="w-4 h-4 text-rose-600 shrink-0"
                          strokeWidth={1.5}
                        />
                      )}
                      <span className="text-xs font-bold text-slate-900">
                        {rule.name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200/80 font-mono tabular-nums">
                        {rule.is_mandatory ? "Mandatory" : "Preferred"} &bull; Wt{" "}
                        {rule.weight}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 pl-6">{rule.reason}</p>
                    {rule.evidence && (
                      <p className="text-[11px] text-slate-500 pl-6 italic">
                        Evidence: {rule.evidence}
                      </p>
                    )}
                  </div>
                  <span className="text-xs font-mono tabular-nums text-slate-500 shrink-0">
                    {Math.round(rule.confidence * 100)}% conf
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right Executive Sidebar Column */}
        <div className="xl:col-span-4 space-y-5">
          {candidate.summary && (
            <Card className="p-5">
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                Candidate Summary
              </h3>
              <p className="text-xs text-slate-700 leading-relaxed">
                {candidate.summary}
              </p>
            </Card>
          )}

          {(candidate.screening_flags?.length ?? 0) > 0 && (
            <Card accent="amber" className="p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800">
                <AlertTriangle
                  className="w-4 h-4 text-amber-600 shrink-0"
                  strokeWidth={1.5}
                />
                Verification &amp; Screening Flags
              </div>
              <ul className="list-disc pl-5 text-xs text-slate-700 space-y-1">
                {candidate.screening_flags?.map((flag, i) => (
                  <li key={i}>{flag}</li>
                ))}
              </ul>
            </Card>
          )}

          {highlights.length > 0 && (
            <Card className="p-5 space-y-3">
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Distinctive Candidate Highlights
              </h3>
              <div className="space-y-2.5">
                {highlights.map((hl, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-slate-900">
                        {hl.title}
                      </span>
                      <StatusPill
                        variant="navy"
                        className="text-[10px] uppercase shrink-0"
                      >
                        {hl.category}
                      </StatusPill>
                    </div>
                    {hl.impact && (
                      <p className="text-slate-600 leading-relaxed">
                        {hl.impact}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {jdEval && jdEval.interview_probes.length > 0 && (
            <Card className="p-5 space-y-2.5">
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <HelpCircle
                  className="w-3.5 h-3.5 text-navy-900"
                  strokeWidth={1.5}
                />
                Suggested Committee Interview Probes
              </h3>
              <ul className="list-disc pl-4 text-xs text-slate-700 space-y-1.5 leading-relaxed">
                {jdEval.interview_probes.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
