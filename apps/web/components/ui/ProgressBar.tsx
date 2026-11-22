"use client";

import React from "react";

export type ProgressVariant = "navy" | "emerald" | "amber" | "rose";

const BAR_CLASSES: Record<ProgressVariant, string> = {
  navy: "bg-navy-900",
  emerald: "bg-emerald-600",
  amber: "bg-amber-500",
  rose: "bg-rose-600",
};

interface ProgressBarProps {
  value: number;
  max?: number;
  minVisiblePct?: number;
  variant?: ProgressVariant;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  minVisiblePct = 0,
  variant = "navy",
  className = "",
}) => {
  const safeMax = max > 0 ? max : 100;
  const rawPct = Math.round((value / safeMax) * 100);
  const clamped = Math.min(
    100,
    Math.max(value > 0 ? minVisiblePct : 0, rawPct)
  );

  return (
    <div
      className={`h-1.5 bg-slate-100 rounded-full overflow-hidden ${className}`.trim()}
    >
      <div
        className={`h-full rounded-full transition-all ${BAR_CLASSES[variant]}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
};
