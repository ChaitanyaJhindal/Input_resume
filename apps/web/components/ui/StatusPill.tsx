"use client";

import React from "react";

export type PillVariant = "emerald" | "amber" | "rose" | "navy" | "neutral";

const PILL_CLASSES: Record<PillVariant, string> = {
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
  amber: "bg-amber-50 text-amber-800 border-amber-200/80",
  rose: "bg-rose-50 text-rose-700 border-rose-200/80",
  navy: "bg-navy-50 text-navy-900 border-navy-200/80",
  neutral: "bg-slate-100/80 text-slate-700 border-slate-200/80",
};

interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: PillVariant;
  mono?: boolean;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  variant = "neutral",
  mono = false,
  className = "",
  children,
  ...rest
}) => {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
        mono ? "font-mono tabular-nums" : ""
      } ${PILL_CLASSES[variant]} ${className}`.trim()}
      {...rest}
    >
      {children}
    </span>
  );
};

export function eligibilityPillVariant(status: string): PillVariant {
  if (status === "eligible") return "emerald";
  if (status === "needs_review") return "amber";
  if (status === "disqualified") return "rose";
  return "neutral";
}

export function tierPillVariant(tier: string): PillVariant {
  if (tier === "strong_match") return "emerald";
  if (tier === "strong_alternative_fit") return "navy";
  if (tier === "conditional_review") return "amber";
  if (tier === "low_alignment") return "rose";
  return "neutral";
}

export function requirementStatusVariant(status: string): PillVariant {
  if (status === "met") return "emerald";
  if (status === "compensated") return "navy";
  if (status === "partially_met") return "amber";
  if (status === "gap") return "rose";
  return "neutral";
}

export function approvalStatusVariant(status: string): PillVariant {
  if (status === "approved" || status === "approved_alternative") return "emerald";
  if (status === "interview_recommended") return "navy";
  if (status === "hold") return "amber";
  if (status === "rejected") return "rose";
  return "neutral";
}
