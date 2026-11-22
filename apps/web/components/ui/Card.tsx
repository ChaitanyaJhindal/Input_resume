"use client";

import React from "react";

export type CardAccent = "none" | "navy" | "emerald" | "amber" | "rose";

const ACCENT_CLASSES: Record<CardAccent, string> = {
  none: "",
  navy: "border-l-2 border-l-navy-900",
  emerald: "border-l-2 border-l-emerald-600",
  amber: "border-l-2 border-l-amber-500",
  rose: "border-l-2 border-l-rose-600",
};

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  accent?: CardAccent;
}

export const Card: React.FC<CardProps> = ({
  accent = "none",
  className = "",
  children,
  ...rest
}) => {
  return (
    <div
      className={`bg-white border border-slate-200/80 rounded-lg ${ACCENT_CLASSES[accent]} ${className}`.trim()}
      {...rest}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...rest
}) => (
  <div
    className={`px-5 py-3.5 border-b border-slate-200/80 flex flex-wrap items-center justify-between gap-3 ${className}`.trim()}
    {...rest}
  >
    {children}
  </div>
);

export const CardBody: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...rest
}) => (
  <div className={`p-5 ${className}`.trim()} {...rest}>
    {children}
  </div>
);
