"use client";

import React from "react";

export interface UnderlineTabItem<T extends string> {
  id: T;
  label: string;
  count?: number;
}

interface UnderlineTabsProps<T extends string> {
  items: ReadonlyArray<UnderlineTabItem<T>>;
  activeId: T;
  onChange: (id: T) => void;
  rightSlot?: React.ReactNode;
  className?: string;
}

export function UnderlineTabs<T extends string>({
  items,
  activeId,
  onChange,
  rightSlot,
  className = "",
}: UnderlineTabsProps<T>) {
  return (
    <div
      className={`border-b border-slate-200/80 flex items-center justify-between gap-3 ${className}`.trim()}
    >
      <div className="flex gap-1 overflow-x-auto" role="tablist">
        {items.map((tab) => {
          const isActive = tab.id === activeId;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onChange(tab.id)}
              className={`px-3.5 py-2.5 text-xs font-semibold border-b-2 transition whitespace-nowrap inline-flex items-center gap-1.5 cursor-pointer ${
                isActive
                  ? "border-navy-900 text-navy-900"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={`font-mono tabular-nums text-[11px] px-1.5 py-0.25 rounded-full border ${
                    isActive
                      ? "bg-navy-50 text-navy-900 border-navy-200/80"
                      : "bg-slate-100 text-slate-600 border-slate-200/80"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {rightSlot && <div className="shrink-0 pb-1.5">{rightSlot}</div>}
    </div>
  );
}
