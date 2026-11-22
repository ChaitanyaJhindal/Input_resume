"use client";

import React from "react";
import {
  Users,
  CheckCircle2,
  Clock,
  Award,
  ArrowRight,
  AlertCircle,
  Upload,
  FileText,
} from "lucide-react";
import {
  AnalyticsOverview,
  Candidate,
  JDCandidatesSummary,
  JobDescription,
} from "../../types/candidate";
import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  MetricTile,
  ProgressBar,
  StatusPill,
  eligibilityPillVariant,
  tierPillVariant,
} from "../../components/ui";

interface DashboardOverviewProps {
  analytics: AnalyticsOverview | null;
  candidates: Candidate[];
  reviewQueue: Candidate[];
  activeJd: JobDescription | null;
  jdSummary: JDCandidatesSummary | null;
  onSelectCandidate: (candidate: Candidate) => void;
  onNavigate: (tab: string, filterStatus?: string) => void;
  onOpenUpload: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  analytics,
  candidates,
  reviewQueue,
  activeJd,
  jdSummary,
  onSelectCandidate,
  onNavigate,
  onOpenUpload,
}) => {
  const metrics = analytics?.metrics;
  const totalProcessed = metrics?.processed ?? candidates.length;
  const eligibleCount =
    metrics?.eligible ??
    candidates.filter((c) => c.eligibility_status === "eligible").length;
  const needsReviewCount = metrics?.needs_review ?? reviewQueue.length;
  const avgTeaching = metrics?.average_teaching_years ?? 0;
  const avgLatency = metrics?.average_processing_time_sec ?? 0;

  const eligibleRate =
    totalProcessed > 0 ? Math.round((eligibleCount / totalProcessed) * 100) : 0;

  const degreeDist = analytics?.distributions?.degree ?? [];
  const maxDegreeCount = Math.max(1, ...degreeDist.map((d) => d.count));

  const topCandidates = [...candidates]
    .sort((a, b) => {
      if (activeJd) {
        return (
          (b.jd_evaluation?.dynamic_score ?? -1) -
          (a.jd_evaluation?.dynamic_score ?? -1)
        );
      }
      return b.overall_score - a.overall_score;
    })
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {activeJd && (
        <Card
          accent="navy"
          className="p-4 flex flex-wrap items-center justify-between gap-3"
        >
          <div className="min-w-0">
            <div className="text-[11px] font-bold uppercase tracking-wider text-navy-900">
              Active Dynamic JD Context
            </div>
            <div className="text-sm font-bold text-slate-900 mt-0.5 truncate">
              {activeJd.title}
              {activeJd.department ? ` — ${activeJd.department}` : ""}
            </div>
            {jdSummary && (
              <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-3">
                <span>
                  <strong className="font-mono tabular-nums text-slate-800">
                    {jdSummary.strong_match}
                  </strong>{" "}
                  Strong Match
                </span>
                <span className="text-slate-300">&bull;</span>
                <span>
                  <strong className="font-mono tabular-nums text-slate-800">
                    {jdSummary.strong_alternative_fit}
                  </strong>{" "}
                  Alternative Fit
                </span>
                <span className="text-slate-300">&bull;</span>
                <span>
                  <strong className="font-mono tabular-nums text-slate-800">
                    {jdSummary.approved_count}
                  </strong>{" "}
                  Approved / Shortlisted
                </span>
              </div>
            )}
          </div>
          <Button
            variant="navySubtle"
            size="sm"
            onClick={() => onNavigate("jds")}
          >
            Edit JD Rubric &amp; Weights
          </Button>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricTile
          label="Screened Applicants"
          value={totalProcessed}
          delta={metrics ? `of ${metrics.total_resumes} total` : undefined}
          icon={<Users className="w-4 h-4" strokeWidth={1.5} />}
          subtext={
            <span className="font-mono tabular-nums">
              {metrics?.source_resumes ?? 0} source &bull;{" "}
              {metrics?.uploaded_resumes ?? 0} uploaded
            </span>
          }
          onClick={() => onNavigate("candidates", "all")}
        />

        <MetricTile
          label="Eligible Faculty"
          value={eligibleCount}
          delta={`${eligibleRate}% pass rate`}
          deltaTone="emerald"
          accent="emerald"
          icon={<CheckCircle2 className="w-4 h-4" strokeWidth={1.5} />}
          subtext="Passed mandatory & weighted rules"
          onClick={() => onNavigate("candidates", "eligible")}
        />

        <MetricTile
          label="Review Queue"
          value={needsReviewCount}
          delta={needsReviewCount > 0 ? "awaiting verdict" : "clear"}
          deltaTone={needsReviewCount > 0 ? "amber" : "neutral"}
          accent={needsReviewCount > 0 ? "amber" : "none"}
          icon={<Clock className="w-4 h-4" strokeWidth={1.5} />}
          subtext="Low confidence or grounding flags"
          onClick={() => onNavigate("review")}
        />

        <MetricTile
          label="Avg Teaching Tenure"
          value={avgTeaching}
          unit="yrs"
          icon={<Award className="w-4 h-4" strokeWidth={1.5} />}
          subtext={
            <span>
              Pipeline avg:{" "}
              <span className="font-mono tabular-nums">
                {avgLatency.toFixed(2)}s / CV
              </span>
            </span>
          }
          onClick={() => onNavigate("analytics")}
        />
      </div>

      {totalProcessed === 0 ? (
        <EmptyState
          icon={<FileText className="w-5 h-5" strokeWidth={1.5} />}
          title="No candidates screened yet"
          description="Upload faculty resumes or sync the configured input folder to extract credentials and run eligibility screening."
          action={
            <Button variant="primary" size="md" onClick={onOpenUpload}>
              <Upload className="w-3.5 h-3.5" strokeWidth={1.5} />
              Upload First Resume
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4 gap-2">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Highest Qualification Distribution
                </h2>
                <p className="text-xs text-slate-500">
                  Normalized degree classification across{" "}
                  <span className="font-mono tabular-nums">
                    {totalProcessed}
                  </span>{" "}
                  candidates
                </p>
              </div>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => onNavigate("analytics")}
                className="text-navy-900 hover:text-navy-950"
              >
                Full analytics <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
              </Button>
            </div>

            <div className="space-y-3">
              {degreeDist.map((item) => {
                const share =
                  totalProcessed > 0
                    ? Math.round((item.count / totalProcessed) * 100)
                    : 0;
                return (
                  <div key={item.name}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-slate-700">
                        {item.name}
                      </span>
                      <span className="font-mono tabular-nums text-slate-600">
                        {item.count} ({share}%)
                      </span>
                    </div>
                    <ProgressBar
                      value={item.count}
                      max={maxDegreeCount}
                      minVisiblePct={4}
                      variant="navy"
                    />
                  </div>
                );
              })}
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center justify-between mb-4 gap-2">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Attention Required
                </h2>
                <p className="text-xs text-slate-500">
                  Pending human verification from review queue
                </p>
              </div>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => onNavigate("review")}
                className="text-navy-900 hover:text-navy-950"
              >
                Open queue <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
              </Button>
            </div>

            {reviewQueue.length === 0 ? (
              <div className="py-8 text-center border border-dashed border-slate-200/80 rounded-lg bg-slate-50/50">
                <CheckCircle2
                  className="w-5 h-5 text-emerald-600 mx-auto mb-2"
                  strokeWidth={1.5}
                />
                <p className="text-xs font-medium text-slate-700">
                  Review queue is clear
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  All candidates meet automated confidence thresholds
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-200/60">
                {reviewQueue.slice(0, 4).map((cand) => (
                  <div
                    key={cand.id}
                    className="py-2.5 flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-slate-900 truncate">
                        {cand.name}
                      </div>
                      <div className="text-[11px] text-amber-800 flex items-center gap-1 truncate mt-0.5">
                        <AlertCircle
                          className="w-3 h-3 text-amber-600 shrink-0"
                          strokeWidth={1.5}
                        />
                        <span className="truncate">
                          {cand.review_reasons?.[0] ||
                            "Flagged for manual verification"}
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      size="xs"
                      onClick={() => onSelectCandidate(cand)}
                      className="shrink-0"
                    >
                      Inspect
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {topCandidates.length > 0 && (
        <Card className="overflow-hidden">
          <CardHeader>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                {activeJd
                  ? `Top Candidates for ${activeJd.title}`
                  : "Highest-Scoring Screened Candidates"}
              </h2>
              <p className="text-xs text-slate-500">
                {activeJd
                  ? "Ranked dynamically by active JD fit and compensating-strength evaluation"
                  : "Ranked strictly by deterministic YAML screening rule score"}
              </p>
            </div>
            <Button
              variant="ghost"
              size="xs"
              onClick={() => onNavigate("candidates", "all")}
              className="text-navy-900 hover:text-navy-950"
            >
              View all{" "}
              <span className="font-mono tabular-nums">{totalProcessed}</span>
              <ArrowRight className="w-3 h-3" strokeWidth={1.5} />
            </Button>
          </CardHeader>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200/80 bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  <th className="py-2.5 px-5">Candidate</th>
                  <th className="py-2.5 px-4">Highest Degree</th>
                  <th className="py-2.5 px-4 text-right">Teaching</th>
                  <th className="py-2.5 px-4 text-right">
                    {activeJd ? "JD Fit" : "Rule Score"}
                  </th>
                  <th className="py-2.5 px-4">
                    {activeJd ? "Recommendation" : "Status"}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/60 text-xs">
                {topCandidates.map((cand) => (
                  <tr
                    key={cand.id}
                    onClick={() => onSelectCandidate(cand)}
                    className="even:bg-slate-50/40 hover:bg-slate-100/50 cursor-pointer transition"
                  >
                    <td className="py-3 px-5">
                      <div className="font-semibold text-slate-900">
                        {cand.name}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {cand.highest_institution}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      {cand.highest_degree}
                    </td>
                    <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                      {cand.teaching_years} yrs
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-semibold text-slate-900 tabular-nums">
                      {activeJd
                        ? cand.jd_evaluation
                          ? `${cand.jd_evaluation.dynamic_score.toFixed(1)}%`
                          : "Pending"
                        : `${cand.overall_score.toFixed(1)}%`}
                    </td>
                    <td className="py-3 px-4">
                      {activeJd && cand.jd_evaluation ? (
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
                      ) : (
                        <StatusPill
                          variant={eligibilityPillVariant(
                            cand.eligibility_status
                          )}
                          className="capitalize"
                        >
                          {cand.eligibility_status.replace("_", " ")}
                        </StatusPill>
                      )}
                    </td>
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
