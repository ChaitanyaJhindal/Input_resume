"use client";

import React from "react";
import {
  CheckCircle2,
  XCircle,
  ExternalLink,
  Mail,
  Phone,
  MapPin,
  ShieldCheck,
  Compass,
} from "lucide-react";
import {
  Candidate,
  CandidateJDEvaluation,
  JDApprovalStatus,
  JobDescription,
} from "../../../types/candidate";
import {
  Button,
  Card,
  StatusPill,
  approvalStatusVariant,
  eligibilityPillVariant,
  tierPillVariant,
} from "../../../components/ui";

interface CandidateHeaderCardProps {
  candidate: Candidate;
  activeJd: JobDescription | null;
  jdEval: CandidateJDEvaluation | null | undefined;
  groundingPct: number | null;
  notes: string;
  onNotesChange: (val: string) => void;
  isSavingReview: boolean;
  reviewFeedback: string | null;
  onVerdict: (verdict: "approved" | "rejected") => void;
  onJdApproval: (approvalStatus: JDApprovalStatus) => void;
}

export const CandidateHeaderCard: React.FC<CandidateHeaderCardProps> = ({
  candidate,
  activeJd,
  jdEval,
  groundingPct,
  notes,
  onNotesChange,
  isSavingReview,
  reviewFeedback,
  onVerdict,
  onJdApproval,
}) => {
  const academicLinks = candidate.academic_links ?? [];
  const extVer = candidate.external_verification;

  return (
    <Card className="p-6 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900">
              {candidate.name}
            </h2>
            {jdEval ? (
              <StatusPill
                variant={tierPillVariant(jdEval.recommendation_tier)}
                className="capitalize font-semibold"
              >
                {jdEval.recommendation_tier.replace(/_/g, " ")}
              </StatusPill>
            ) : (
              <StatusPill
                variant={eligibilityPillVariant(candidate.eligibility_status)}
                className="capitalize font-semibold"
              >
                {candidate.eligibility_status.replace("_", " ")}
              </StatusPill>
            )}
            <StatusPill variant="neutral">{candidate.review_status}</StatusPill>
            {jdEval && jdEval.approval_status !== "pending" && (
              <StatusPill
                variant={approvalStatusVariant(jdEval.approval_status)}
                className="capitalize"
              >
                JD: {jdEval.approval_status.replace(/_/g, " ")}
              </StatusPill>
            )}
            <span className="font-mono tabular-nums text-[11px] text-slate-400">
              ID:{candidate.id}
            </span>
          </div>

          {candidate.current_designation && (
            <p className="text-sm text-slate-600">
              {candidate.current_designation}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
            {candidate.email && (
              <span className="inline-flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-slate-400" strokeWidth={1.5} />
                {candidate.email}
              </span>
            )}
            {candidate.phone && (
              <span className="inline-flex items-center gap-1.5 font-mono tabular-nums">
                <Phone className="w-3.5 h-3.5 text-slate-400" strokeWidth={1.5} />
                {candidate.phone}
              </span>
            )}
            {candidate.location && (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-slate-400" strokeWidth={1.5} />
                {candidate.location}
              </span>
            )}
          </div>

          {(academicLinks.length > 0 ||
            (extVer &&
              (extVer.citation_count !== null ||
                extVer.h_index !== null))) && (
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {academicLinks.map((lnk) => (
                <a
                  key={`${lnk.platform}-${lnk.url}`}
                  href={lnk.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-white text-navy-900 border border-slate-200/80 hover:bg-navy-50 hover:border-navy-200 transition"
                >
                  {lnk.verified && (
                    <ShieldCheck
                      className="w-3.5 h-3.5 text-emerald-600"
                      strokeWidth={1.5}
                    />
                  )}
                  <span className="capitalize">
                    {lnk.platform.replace("_", " ")}
                  </span>
                  {lnk.identifier && (
                    <span className="font-mono tabular-nums text-[11px] text-slate-500">
                      ({lnk.identifier})
                    </span>
                  )}
                  <ExternalLink
                    className="w-3 h-3 text-slate-400"
                    strokeWidth={1.5}
                  />
                </a>
              ))}

              {extVer &&
                (extVer.citation_count !== null ||
                  extVer.h_index !== null) && (
                  <StatusPill
                    variant="emerald"
                    mono
                    title={`Verified via ${extVer.match_method}`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
                    Citations: {extVer.citation_count ?? 0} &bull; h-index:{" "}
                    {extVer.h_index ?? 0}
                  </StatusPill>
                )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2.5 shrink-0">
          <div className="px-3.5 py-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 text-center min-w-[96px]">
            <div className="text-[11px] text-slate-500">
              {jdEval ? "JD Fit Score" : "Rule Score"}
            </div>
            <div className="text-lg font-bold font-mono tabular-nums text-navy-900 mt-0.5">
              {(jdEval
                ? jdEval.dynamic_score
                : candidate.overall_score
              ).toFixed(1)}
              %
            </div>
          </div>
          <div className="px-3.5 py-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 text-center min-w-[96px]">
            <div className="text-[11px] text-slate-500">Confidence</div>
            <div className="text-lg font-bold font-mono tabular-nums text-slate-900 mt-0.5">
              {Math.round(
                (jdEval ? jdEval.confidence : candidate.confidence) * 100
              )}
              %
            </div>
          </div>
          <div className="px-3.5 py-2.5 rounded-md bg-slate-50/70 border border-slate-200/80 text-center min-w-[96px]">
            <div className="text-[11px] text-slate-500">Grounding</div>
            <div className="text-lg font-bold font-mono tabular-nums text-slate-900 mt-0.5">
              {groundingPct !== null ? `${groundingPct}%` : "N/A"}
            </div>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-slate-200/60 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder="Committee decision notes (optional)..."
            className="flex-1 min-w-[220px] px-3 py-1.5 text-xs bg-slate-50/70 border border-slate-200/80 rounded-md focus:outline-none focus:bg-white focus:border-navy-900"
          />
          {activeJd && jdEval ? (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onJdApproval("approved")}
                disabled={isSavingReview}
              >
                <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                Shortlist
              </Button>
              <Button
                variant="navySubtle"
                size="sm"
                onClick={() => onJdApproval("approved_alternative")}
                disabled={isSavingReview}
              >
                <Compass className="w-3.5 h-3.5" strokeWidth={1.5} />
                Approve Alt Track
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onJdApproval("interview_recommended")}
                disabled={isSavingReview}
              >
                Interview
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onJdApproval("hold")}
                disabled={isSavingReview}
              >
                Hold
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => onJdApproval("rejected")}
                disabled={isSavingReview}
              >
                <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                Decline
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onVerdict("approved")}
                disabled={isSavingReview}
              >
                <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                Approve Eligible
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => onVerdict("rejected")}
                disabled={isSavingReview}
              >
                <XCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                Disqualify
              </Button>
            </>
          )}
        </div>
        {reviewFeedback && (
          <p className="text-xs font-medium text-navy-900">{reviewFeedback}</p>
        )}
      </div>
    </Card>
  );
};
