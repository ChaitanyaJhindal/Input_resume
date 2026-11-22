"use client";

import React from "react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "navySubtle"
  | "ghost"
  | "danger"
  | "dangerSolid";

export type ButtonSize = "xs" | "sm" | "md";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-navy-900 text-white border border-navy-900 hover:bg-navy-950 hover:border-navy-950",
  secondary:
    "bg-white text-slate-700 border border-slate-200/80 hover:bg-slate-50 hover:border-slate-300",
  navySubtle:
    "bg-navy-50 text-navy-900 border border-navy-200/80 hover:bg-navy-100/70",
  ghost:
    "bg-transparent text-slate-600 border border-transparent hover:text-slate-900 hover:bg-slate-100/80",
  danger:
    "bg-white text-rose-700 border border-rose-200/80 hover:bg-rose-50",
  dangerSolid:
    "bg-rose-600 text-white border border-rose-600 hover:bg-rose-700",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  xs: "px-2.5 py-1 text-[11px] font-medium",
  sm: "px-3 py-1.5 text-xs font-medium",
  md: "px-3.5 py-2 text-xs font-semibold",
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "secondary",
  size = "sm",
  type = "button",
  className = "",
  children,
  ...rest
}) => {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  );
};
