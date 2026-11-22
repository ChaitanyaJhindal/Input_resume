"use client";

import React from "react";

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = "",
}) => {
  return (
    <div
      className={`bg-white border border-slate-200/80 rounded-lg p-10 text-center ${className}`.trim()}
    >
      <div className="w-10 h-10 rounded-lg border border-slate-200/80 bg-slate-50 flex items-center justify-center mx-auto mb-3 text-slate-500">
        {icon}
      </div>
      <h2 className="text-sm font-bold text-slate-900">{title}</h2>
      <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
};
