"use client";

import React, { useEffect, useState } from "react";
import {
  GitCompare,
  CheckCircle2,
  XCircle,
  X,
  Plus,
  ExternalLink,
} from "lucide-react";
import {
  Candidate,
  JobDescription,
  ScreeningRuleConfig,
} from "../../types/candidate";
import { compareCandidates } from "../../lib/api";
import {
  Button,
  Card,
  EmptyState,
  StatusPill,
  eligibilityPillVariant,
  requirementStatusVariant,
  tierPillVariant,
} from "../../components/ui";

interface CandidateComparisonViewProps {
  selectedIds: string[];
  allCandidates: Candidate[];
  rules: ScreeningRuleConfig[];
  activeJd: JobDescription | null;
  onToggleCompare: (id: string) => void;
  onClearSelection: () => void;
  onSelectCandidate: (candidate: Candidate) => void;
}

interface ComparisonRow {
  label: string;
  numericValue?: (c: Candidate) => number;
  render: (c: Candidate, isBest: boolean) => React.ReactNode;
}

const COMPARE_ROWS: ComparisonRow[] = [
  {
    label: "Eligibility Status",
    render: (c) => (
      <StatusPill
        variant={eligibilityPillVariant(c.eligibility_status)}
        className="capitalize font-semibold"
      >
        {c.eligibility_status.replace("_", " ")}
      </StatusPill>
    ),
  },
  {
    label: "Rule Score",
    numericValue: (c) => c.overall_score,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums font-bold ${
          isBest ? "text-navy-900" : "text-slate-900"
        }`}
      >
        {c.overall_score.toFixed(1)}%
      </span>
    ),
  },
  {
    label: "Extraction Confidence",
    numericValue: (c) => c.confidence,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums ${
          isBest ? "font-semibold text-navy-900" : "text-slate-700"
        }`}
      >
        {Math.round(c.confidence * 100)}%
      </span>
    ),
  },
  {
    label: "Source Grounding",
    numericValue: (c) => c.grounding_score ?? -1,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums ${
          isBest ? "font-semibold text-navy-900" : "text-slate-700"
        }`}
      >
        {c.grounding_score !== null && c.grounding_score !== undefined
          ? `${Math.round(c.grounding_score * 100)}%`
          : "N/A"}
      </span>
    ),
  },
  {
    label: "Highest Degree",
    render: (c) => (
      <span className="font-medium text-slate-900">{c.highest_degree}</span>
    ),
  },
  {
    label: "Institution & Tier",
    render: (c) => (
      <div>
        <div className="text-slate-900 font-medium">
          {c.highest_institution}
        </div>
        <div className="text-[11px] text-slate-500">
          {c.highest_institution_category}
        </div>
      </div>
    ),
  },
  {
    label: "Teaching Experience",
    numericValue: (c) => c.teaching_years,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums font-semibold ${
          isBest ? "text-navy-900" : "text-slate-800"
        }`}
      >
        {c.teaching_years} yrs
      </span>
    ),
  },
  {
    label: "Research Experience",
    numericValue: (c) => c.research_years,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums ${
          isBest ? "font-semibold text-navy-900" : "text-slate-700"
        }`}
      >
        {c.research_years} yrs
      </span>
    ),
  },
  {
    label: "Industry / Admin",
    render: (c) => (
      <span className="font-mono tabular-nums text-slate-700">
        {c.industry_years} / {c.administrative_years ?? 0} yrs
      </span>
    ),
  },
  {
    label: "Total Career Tenure",
    numericValue: (c) => c.total_years,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums ${
          isBest ? "font-semibold text-navy-900" : "text-slate-800"
        }`}
      >
        {c.total_years} yrs
      </span>
    ),
  },
  {
    label: "Publications",
    numericValue: (c) => c.publications_count,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums font-semibold ${
          isBest ? "text-navy-900" : "text-slate-800"
        }`}
      >
        {c.publications_count}
      </span>
    ),
  },
  {
    label: "Courses Taught",
    numericValue: (c) =>
      c.courses_taught?.length ?? c.courses_taught_count ?? 0,
    render: (c, isBest) => (
      <span
        className={`font-mono tabular-nums ${
          isBest ? "font-semibold text-navy-900" : "text-slate-800"
        }`}
      >
        {c.courses_taught?.length ?? c.courses_taught_count ?? 0}
      </span>
    ),
  },
  {
    label: "Academic Links & Citations",
    render: (c) => (
      <div className="text-[11px] text-slate-700 space-y-0.5">
        <div className="font-mono tabular-nums">
          {c.academic_links?.length ?? 0} verified links
        </div>
        {c.external_citations !== null &&
          c.external_citations !== undefined && (
            <div className="font-mono tabular-nums text-emerald-700">
              {c.external_citations} cites / h:{c.external_h_index ?? 0}
            </div>
          )}
      </div>
    ),
  },
  {
    label: "Review Status",
    render: (c) => <span className="text-slate-700">{c.review_status}</span>,
  },
];

export const CandidateComparisonView: React.FC<
  CandidateComparisonViewProps
> = ({
  selectedIds,
  allCandidates,
  rules,
  activeJd,
  onToggleCompare,
  onClearSelection,
  onSelectCandidate,
}) => {
  const [compared, setCompared] = useState<Candidate[]>([]);
  const [addCandidateId, setAddCandidateId] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (selectedIds.length < 2) {
        const local = allCandidates.filter((c) => selectedIds.includes(c.id));
        if (!cancelled) {
          setCompared(local);
          setErrorMsg(null);
        }
        return;
      }
      try {
        const res = await compareCandidates(selectedIds);
        if (!cancelled) {
          const byId = new Map(allCandidates.map((c) => [c.id, c]));
          setCompared(
            res.map((item) => ({
              ...item,
              jd_evaluation:
                byId.get(item.id)?.jd_evaluation ?? item.jd_evaluation,
            }))
          );
          setErrorMsg(null);
        }
      } catch (err) {
        if (!cancelled) {
          setErrorMsg(
            err instanceof Error ? err.message : "Failed to load comparison"
          );
          setCompared(allCandidates.filter((c) => selectedIds.includes(c.id)));
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedIds, allCandidates]);

  const unselectedCandidates = allCandidates.filter(
    (c) => !selectedIds.includes(c.id)
  );

  const handleAddCandidate = () => {
    if (!addCandidateId || selectedIds.length >= 4) return;
    onToggleCompare(addCandidateId);
    setAddCandidateId("");
  };

  const ruleHeaders: Array<{ id: string; name: string }> =
    rules.length > 0
      ? rules.map((r) => ({ id: r.id, name: r.name }))
      : Array.from(
          new Map(
            compared
              .flatMap((c) => c.rules_evaluated ?? [])
              .map((ev) => [ev.rule_id, { id: ev.rule_id, name: ev.name }])
          ).values()
        );

  const jdReqHeaders: Array<{ id: string; label: string }> = activeJd
    ? Array.from(
        new Map(
          compared
            .flatMap((c) => c.jd_evaluation?.requirement_matrix ?? [])
            .map((rm) => [
              rm.requirement_id,
              { id: rm.requirement_id, label: rm.label },
            ])
        ).values()
      )
    : [];

  const maxDynamicScore = Math.max(
    -1,
    ...compared.map((c) => c.jd_evaluation?.dynamic_score ?? -1)
  );

  return (
    <div className="space-y-5">
      <Card className="p-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-900">
            Side-by-Side Candidate Matrix (
            <span className="font-mono tabular-nums">
              {selectedIds.length}/4
            </span>
            )
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Select 2 to 4 applicants to compare verified credentials, JD alignment, and per-rule checks.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {selectedIds.length < 4 && unselectedCandidates.length > 0 && (
            <div className="flex items-center gap-1.5">
              <select
                value={addCandidateId}
                onChange={(e) => setAddCandidateId(e.target.value)}
                aria-label="Choose candidate to add to comparison"
                className="text-xs px-2.5 py-1.5 rounded-md border border-slate-200/80 bg-white text-slate-700 max-w-[220px] focus:outline-none focus:border-navy-900"
              >
                <option value="">Add candidate to compare...</option>
                {unselectedCandidates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.overall_score.toFixed(0)}%)
                  </option>
                ))}
              </select>
              <Button
                variant="primary"
                size="sm"
                onClick={handleAddCandidate}
                disabled={!addCandidateId}
              >
                <Plus className="w-3.5 h-3.5" strokeWidth={1.5} />
                Add
              </Button>
            </div>
          )}

          {selectedIds.length > 0 && (
            <Button variant="secondary" size="sm" onClick={onClearSelection}>
              Clear Selection
            </Button>
          )}
        </div>
      </Card>

      {errorMsg && (
        <Card accent="amber" className="p-3 text-xs text-amber-800">
          {errorMsg}
        </Card>
      )}

      {compared.length < 2 ? (
        <EmptyState
          icon={<GitCompare className="w-5 h-5" strokeWidth={1.5} />}
          title="Select at least 2 candidates to compare"
          description={`Use the dropdown above or check boxes in the Candidate Pool table.${
            compared.length === 1
              ? ` Currently selected: ${compared[0].name}.`
              : ""
          }`}
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200/80 bg-slate-50/80">
                  <th className="py-3.5 px-4 text-[11px] font-bold uppercase tracking-wider text-slate-500 w-52">
                    Criterion
                  </th>
                  {compared.map((cand) => (
                    <th
                      key={cand.id}
                      className="py-3.5 px-4 min-w-[200px] border-l border-slate-200/60"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <button
                          type="button"
                          onClick={() => onSelectCandidate(cand)}
                          className="text-left group cursor-pointer"
                        >
                          <div className="text-xs font-bold text-slate-900 group-hover:text-navy-900 inline-flex items-center gap-1">
                            {cand.name}
                            <ExternalLink
                              className="w-3 h-3 opacity-60"
                              strokeWidth={1.5}
                            />
                          </div>
                          <div className="text-[11px] font-normal font-mono text-slate-500 truncate max-w-[180px]">
                            {cand.file_name}
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => onToggleCompare(cand.id)}
                          title="Remove from comparison"
                          aria-label={`Remove ${cand.name}`}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded cursor-pointer"
                        >
                          <X className="w-3.5 h-3.5" strokeWidth={1.5} />
                        </button>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-200/60 text-xs">
                {activeJd && (
                  <tr className="bg-navy-50/40">
                    <td className="py-3 px-4 font-bold text-navy-900">
                      Active JD Fit ({activeJd.title})
                    </td>
                    {compared.map((cand) => {
                      const score = cand.jd_evaluation?.dynamic_score ?? -1;
                      const isTop = score >= 0 && score === maxDynamicScore;
                      return (
                        <td
                          key={`${cand.id}-jd-fit`}
                          className="py-3 px-4 border-l border-slate-200/60"
                        >
                          {cand.jd_evaluation ? (
                            <div className="space-y-1">
                              <div
                                className={`font-mono tabular-nums font-bold ${
                                  isTop ? "text-navy-900" : "text-slate-900"
                                }`}
                              >
                                {cand.jd_evaluation.dynamic_score.toFixed(1)}%
                              </div>
                              <StatusPill
                                variant={tierPillVariant(
                                  cand.jd_evaluation.recommendation_tier
                                )}
                                className="capitalize"
                              >
                                {cand.jd_evaluation.recommendation_tier.replace(
                                  /_/g,
                                  " "
                                )}
                              </StatusPill>
                            </div>
                          ) : (
                            <span className="text-slate-400">
                              Not evaluated
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                )}

                {COMPARE_ROWS.map((row) => {
                  const maxVal = row.numericValue
                    ? Math.max(...compared.map((c) => row.numericValue!(c)))
                    : null;
                  return (
                    <tr key={row.label} className="hover:bg-slate-50/60">
                      <td className="py-3 px-4 font-semibold text-slate-600 bg-slate-50/40">
                        {row.label}
                      </td>
                      {compared.map((cand) => {
                        const val = row.numericValue
                          ? row.numericValue(cand)
                          : null;
                        const isBest =
                          maxVal !== null &&
                          val !== null &&
                          val > 0 &&
                          val === maxVal;
                        return (
                          <td
                            key={`${cand.id}-${row.label}`}
                            className="py-3 px-4 border-l border-slate-200/60"
                          >
                            {row.render(cand, isBest)}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}

                {jdReqHeaders.length > 0 && (
                  <>
                    <tr className="bg-slate-100/70">
                      <td
                        colSpan={compared.length + 1}
                        className="py-2 px-4 text-[11px] font-bold uppercase tracking-wider text-slate-600"
                      >
                        JD Requirement Alignment
                      </td>
                    </tr>
                    {jdReqHeaders.map((req) => (
                      <tr key={req.id} className="hover:bg-slate-50/60">
                        <td className="py-3 px-4 font-semibold text-slate-600 bg-slate-50/40">
                          {req.label}
                        </td>
                        {compared.map((cand) => {
                          const rm = (
                            cand.jd_evaluation?.requirement_matrix ?? []
                          ).find((r) => r.requirement_id === req.id);
                          if (!rm) {
                            return (
                              <td
                                key={`${cand.id}-${req.id}`}
                                className="py-3 px-4 border-l border-slate-200/60 text-slate-400"
                              >
                                Not evaluated
                              </td>
                            );
                          }
                          return (
                            <td
                              key={`${cand.id}-${req.id}`}
                              className="py-3 px-4 border-l border-slate-200/60 space-y-1"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <StatusPill
                                  variant={requirementStatusVariant(rm.status)}
                                  className="text-[10px] uppercase font-bold"
                                >
                                  {rm.status.replace("_", " ")}
                                </StatusPill>
                                <span className="font-mono tabular-nums text-slate-700 font-medium">
                                  {rm.score.toFixed(0)}%
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-500 line-clamp-2">
                                {rm.rationale}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </>
                )}

                {ruleHeaders.length > 0 && (
                  <tr className="bg-slate-100/70">
                    <td
                      colSpan={compared.length + 1}
                      className="py-2 px-4 text-[11px] font-bold uppercase tracking-wider text-slate-600"
                    >
                      Baseline Screening Rule Breakdown
                    </td>
                  </tr>
                )}

                {ruleHeaders.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-50/60">
                    <td className="py-3 px-4 font-semibold text-slate-600 bg-slate-50/40">
                      {rule.name}
                    </td>
                    {compared.map((cand) => {
                      const ev = (cand.rules_evaluated ?? []).find(
                        (r) => r.rule_id === rule.id
                      );
                      if (!ev) {
                        return (
                          <td
                            key={`${cand.id}-${rule.id}`}
                            className="py-3 px-4 border-l border-slate-200/60 text-slate-400"
                          >
                            Not evaluated
                          </td>
                        );
                      }
                      return (
                        <td
                          key={`${cand.id}-${rule.id}`}
                          className="py-3 px-4 border-l border-slate-200/60"
                        >
                          <div className="flex items-center gap-1.5 font-semibold">
                            {ev.status === "pass" ? (
                              <CheckCircle2
                                className="w-3.5 h-3.5 text-emerald-600 shrink-0"
                                strokeWidth={1.5}
                              />
                            ) : (
                              <XCircle
                                className="w-3.5 h-3.5 text-rose-600 shrink-0"
                                strokeWidth={1.5}
                              />
                            )}
                            <span
                              className={
                                ev.status === "pass"
                                  ? "text-emerald-700"
                                  : "text-rose-700"
                              }
                            >
                              {ev.status === "pass" ? "Pass" : "Fail"}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-500 mt-0.5">
                            {ev.reason}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
