"use client";

import React from "react";
import {
  Activity,
  Cpu,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  Clock,
  XCircle,
  FileText,
  Layers,
} from "lucide-react";
import { AnalyticsOverview, Candidate } from "../../types/candidate";
import {
  Card,
  MetricTile,
  ProgressBar,
  StatusPill,
} from "../../components/ui";

interface AnalyticsViewProps {
  analytics: AnalyticsOverview | null;
  candidates: Candidate[];
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({
  analytics,
  candidates,
}) => {
  if (!analytics) {
    return (
      <Card className="p-8 text-center text-sm text-slate-500">
        Analytics data is not available yet.
      </Card>
    );
  }

  const { metrics, distributions, telemetry, groq_pool } = analytics;
  const totalProcessed = Math.max(1, metrics.processed || candidates.length);
  const scoreBrackets = distributions.score_brackets ?? [];
  const expBrackets = distributions.experience ?? [];
  const rulePassRates = distributions.rule_pass_rates ?? [];
  const instDist = distributions.institution_category ?? [];
  const groundingBrackets = distributions.grounding_brackets ?? [];

  const maxScoreCount = Math.max(1, ...scoreBrackets.map((s) => s.count));
  const maxExpCount = Math.max(1, ...expBrackets.map((e) => e.count));
  const maxInstCount = Math.max(1, ...instDist.map((i) => i.count));
  const totalGrounding = groundingBrackets.reduce((acc, g) => acc + g.count, 0);

  return (
    <div className="space-y-6">
      <Card className="p-5 space-y-4">
        <h2 className="text-sm font-bold text-slate-900">
          Recruitment Pipeline Funnel
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <MetricTile
            label="Total Resumes"
            value={metrics.total_resumes}
            icon={<FileText className="w-4 h-4" strokeWidth={1.5} />}
            subtext={
              <span className="font-mono tabular-nums">
                {metrics.source_resumes} src + {metrics.uploaded_resumes} upl
              </span>
            }
          />
          <MetricTile
            label="Screened"
            value={metrics.processed}
            accent="navy"
            icon={
              <Layers className="w-4 h-4 text-navy-900" strokeWidth={1.5} />
            }
            subtext={
              <span className="font-mono tabular-nums">
                Avg {metrics.average_processing_time_sec.toFixed(2)}s / CV
              </span>
            }
          />
          <MetricTile
            label="Eligible"
            value={metrics.eligible}
            accent="emerald"
            delta={`${Math.round((metrics.eligible / totalProcessed) * 100)}%`}
            deltaTone="emerald"
            icon={
              <CheckCircle2
                className="w-4 h-4 text-emerald-600"
                strokeWidth={1.5}
              />
            }
            subtext="Of screened pool"
          />
          <MetricTile
            label="Needs Review"
            value={metrics.needs_review}
            accent="amber"
            icon={
              <Clock className="w-4 h-4 text-amber-600" strokeWidth={1.5} />
            }
            subtext="Active review queue"
          />
          <MetricTile
            label="Disqualified"
            value={metrics.disqualified}
            accent="rose"
            icon={
              <XCircle className="w-4 h-4 text-rose-600" strokeWidth={1.5} />
            }
            subtext="Mandatory rule missed"
          />
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Rule-by-Rule Pass Rates
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Evaluation outcomes across active YAML rules
          </p>
          {rulePassRates.length === 0 ? (
            <p className="text-xs text-slate-500">No rule metrics recorded.</p>
          ) : (
            <div className="space-y-3">
              {rulePassRates.map((rule) => (
                <div key={rule.rule_id}>
                  <div className="flex items-center justify-between text-xs mb-1 gap-2">
                    <span className="font-medium text-slate-800 truncate">
                      {rule.name}{" "}
                      <span className="text-[10px] text-slate-400">
                        ({rule.is_mandatory ? "Mandatory" : "Preferred"})
                      </span>
                    </span>
                    <span className="font-mono tabular-nums text-slate-600 shrink-0">
                      {rule.passed}/{rule.total} ({rule.pass_rate_pct}%)
                    </span>
                  </div>
                  <ProgressBar
                    value={rule.pass_rate_pct}
                    max={100}
                    minVisiblePct={2}
                    variant={
                      rule.pass_rate_pct >= 70
                        ? "emerald"
                        : rule.pass_rate_pct >= 40
                        ? "amber"
                        : "rose"
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Institution Category Distribution
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Highest academic degree affiliation taxonomy
          </p>
          <div className="space-y-3">
            {instDist.map((item) => (
              <div key={item.name}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700">
                    {item.name}
                  </span>
                  <span className="font-mono tabular-nums text-slate-600">
                    {item.count}
                  </span>
                </div>
                <ProgressBar
                  value={item.count}
                  max={maxInstCount}
                  minVisiblePct={4}
                  variant="navy"
                />
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Screening Score Distribution
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Weighted percentage score brackets
          </p>
          <div className="space-y-3">
            {scoreBrackets.map((item) => (
              <div key={item.bracket}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium font-mono tabular-nums text-slate-700">
                    {item.bracket}
                  </span>
                  <span className="font-mono tabular-nums text-slate-600">
                    {item.count}
                  </span>
                </div>
                <ProgressBar
                  value={item.count}
                  max={maxScoreCount}
                  minVisiblePct={4}
                  variant="navy"
                />
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Teaching Experience Brackets
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Interval-merged academic teaching tenure (avg{" "}
            <span className="font-mono tabular-nums">
              {metrics.average_teaching_years} yrs
            </span>
            )
          </p>
          <div className="space-y-3">
            {expBrackets.map((item) => (
              <div key={item.bracket}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium font-mono tabular-nums text-slate-700">
                    {item.bracket}
                  </span>
                  <span className="font-mono tabular-nums text-slate-600">
                    {item.count}
                  </span>
                </div>
                <ProgressBar
                  value={item.count}
                  max={maxExpCount}
                  minVisiblePct={4}
                  variant="navy"
                />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-5 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck
                className="w-4 h-4 text-emerald-600"
                strokeWidth={1.5}
              />
              Source Grounding Quality
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Anti-hallucination verification coverage (
              <span className="font-mono tabular-nums">{totalGrounding}</span>{" "}
              measured)
            </p>
          </div>

          <div className="space-y-3">
            {groundingBrackets.map((gb) => {
              const pct =
                totalGrounding > 0
                  ? Math.round((gb.count / totalGrounding) * 100)
                  : 0;
              return (
                <div key={gb.bracket}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-slate-700">
                      {gb.bracket}
                    </span>
                    <span className="font-mono tabular-nums text-slate-600">
                      {gb.count} ({pct}%)
                    </span>
                  </div>
                  <ProgressBar
                    value={pct}
                    max={100}
                    variant={
                      gb.bracket.startsWith("High")
                        ? "emerald"
                        : gb.bracket.startsWith("Moderate")
                        ? "amber"
                        : "rose"
                    }
                  />
                </div>
              );
            })}
          </div>
        </Card>

        <Card className="p-5 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-navy-900" strokeWidth={1.5} />
            Hybrid Inference &amp; API Key Pool Telemetry
          </h3>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">Deterministic</div>
              <div className="text-base font-bold text-slate-900 font-mono tabular-nums mt-0.5">
                {telemetry.deterministic_resolutions}
              </div>
            </div>
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">JEV Micro</div>
              <div className="text-base font-bold text-slate-900 font-mono tabular-nums mt-0.5">
                {telemetry.jev_decision_calls}
              </div>
            </div>
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">Groq Calls</div>
              <div className="text-base font-bold text-slate-900 font-mono tabular-nums mt-0.5">
                {telemetry.groq_api_calls}
              </div>
            </div>
            <div className="p-3 rounded-md bg-slate-50/70 border border-slate-200/80">
              <div className="text-slate-500">Escalations</div>
              <div className="text-base font-bold text-slate-900 font-mono tabular-nums mt-0.5">
                {telemetry.escalations}
              </div>
            </div>
          </div>

          {groq_pool && (
            <div className="pt-3 border-t border-slate-200/60 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700 flex items-center gap-1.5 font-mono tabular-nums">
                  <KeyRound
                    className="w-3.5 h-3.5 text-slate-500"
                    strokeWidth={1.5}
                  />
                  Groq Key Pool ({groq_pool.active_available_keys}/
                  {groq_pool.total_keys} ready)
                </span>
                <span className="text-[11px] font-mono tabular-nums text-slate-500 flex items-center gap-1">
                  <Activity className="w-3 h-3" strokeWidth={1.5} />
                  {groq_pool.rotations_handled} rotations
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {groq_pool.key_distribution.map((k) => (
                  <StatusPill
                    key={k.key_index}
                    variant={k.cooling_down ? "amber" : "emerald"}
                    mono
                  >
                    Key #{k.key_index + 1}: {k.requests} req
                    {k.cooling_down ? " (cooldown)" : ""}
                  </StatusPill>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
