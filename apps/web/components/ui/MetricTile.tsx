"use client";

import React from "react";
import type { CardAccent } from "./Card";

interface MetricTileProps {
  label: string;
  value: React.ReactNode;
  unit?: string;
  delta?: string;
  deltaTone?: "neutral" | "emerald" | "amber" | "rose" | "navy";
  subtext?: React.ReactNode;
  icon?: React.ReactNode;
  accent?: CardAccent;
  onClick?: () => void;
  className?: string;
}

const ACCENT_LINE: Record<CardAccent, string> = {
  none: "",
  navy: "border-t-2 border-t-navy-900",
  emerald: "border-t-2 border-t-emerald-600",
  amber: "border-t-2 border-t-amber-500",
  rose: "border-t-2 border-t-rose-600",
};

const DELTA_TEXT: Record<NonNullable<MetricTileProps["deltaTone"]>, string> = {
  neutral: "text-slate-500",
  emerald: "text-emerald-700",
  amber: "text-amber-700",
  rose: "text-rose-700",
  navy: "text-navy-900",
};

export const MetricTile: React.FC<MetricTileProps> = ({
  label,
  value,
  unit,
  delta,
  deltaTone = "neutral",
  subtext,
  icon,
  accent = "none",
  onClick,
  className = "",
}) => {
  const baseClass = `w-full text-left bg-white border border-slate-200/80 rounded-lg p-4 transition ${
    ACCENT_LINE[accent]
  } ${
    onClick ? "hover:border-navy-900/35 cursor-pointer" : ""
  } ${className}`.trim();

  const inner = (
    <>
      <div className="flex items-center justify-between gap-2 text-xs font-medium text-slate-500">
        <span className="truncate">{label}</span>
        {icon && <span className="text-slate-400 shrink-0">{icon}</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-2 min-w-0">
        <span className="text-2xl font-bold text-slate-900 font-mono tabular-nums tracking-tight">
          {value}
        </span>
        {unit && (
          <span className="text-xs text-slate-500 font-mono tabular-nums">
            {unit}
          </span>
        )}
        {delta && (
          <span
            className={`text-xs font-medium font-mono tabular-nums ${DELTA_TEXT[deltaTone]}`}
          >
            {delta}
          </span>
        )}
      </div>
      {subtext && (
        <div className="mt-1.5 text-[11px] text-slate-500 truncate">
          {subtext}
        </div>
      )}
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={baseClass}>
        {inner}
      </button>
    );
  }

  return <div className={baseClass}>{inner}</div>;
};
