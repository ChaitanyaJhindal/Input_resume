"use client";

import React from "react";

interface SectionHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  uppercase?: boolean;
  className?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  subtitle,
  icon,
  actions,
  uppercase = false,
  className = "",
}) => {
  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 ${className}`.trim()}
    >
      <div className="min-w-0">
        <h3
          className={`flex items-center gap-2 ${
            uppercase
              ? "text-[11px] font-bold uppercase tracking-wider text-slate-500"
              : "text-sm font-bold text-slate-900"
          }`}
        >
          {icon && <span className="text-slate-500 shrink-0">{icon}</span>}
          <span className="truncate">{title}</span>
        </h3>
        {subtitle && (
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        )}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
};
