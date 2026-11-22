---
trigger: glob
description: Enforce FacultyScreen anti-slop Tailwind v4 and UI standards across frontend code
globs: "apps/web/**/*.tsx, apps/web/**/*.css"
---

# FacultyScreen UI Standards (Anti-Slop + Academic Authority)

## 1. Forbidden Patterns ("AI Slop")
- Never use CSS gradients (`bg-gradient-*`, `bg-linear-*`, `linear-gradient`), decorative emojis, `shadow-md`/`shadow-lg`/`hover:shadow-sm` on static or grid cards, or `rounded-2xl`/`rounded-3xl`/`rounded-xl` on data containers.
- Never use `Sparkles` as a generic AI badge or empty-state icon — use domain icons (`Scale`, `Compass`, `BookOpen`, `FileText`, `GraduationCap`, `ShieldCheck`, `Award`).
- Never render multi-colour solid "rainbow" button rows or paint full KPI/funnel cards in saturated pastel fills (`bg-indigo-50/70`, `bg-blue-50/60`, `bg-teal-50`).
- Never use `bg-slate-900` or `bg-blue-600` for primary CTAs or heavy dark sidebar chrome; reserve Collegiate Navy (`#1e3a8a` / `navy-900`) for primary actions and active navigation.

## 2. Structural Geometry, Borders & Iconography
- Borders: `1px` hairlines (`border-slate-200/80`) on all cards, panels, tables, and inputs; `divide-slate-200/60` for table/list partitions.
- Radii: `rounded-lg` (8px) for data containers, cards, panels, and modals; `rounded-md` (6px) for buttons, inputs, selects, and inner tiles; `rounded-full` strictly for compact semantic status pills and link badges.
- Shadows: none on static/grid cards or buttons. At most `shadow-xl` on floating modal dialogs (`UploadModal`).
- Icons: all `lucide-react` icons MUST explicitly pass `strokeWidth={1.5}`.

## 3. 90 / 8 / 2 Colour Budget
- **90% Neutral Canvas & Surfaces:** `#f8fafc` (`bg-slate-50`) canvas, `#ffffff` (`bg-white`) cards/shell, `#0f172a` (`text-slate-900`) primary ink, `#475569`/`#64748b` secondary ink.
- **8% Collegiate Navy (`#1e3a8a` / `navy-900`, hover `navy-950`, tint `navy-50`):** Primary CTAs, active sidebar indicator, active underline tabs, chart bars, active JD focus borders, and verified academic links.
- **2% Soft Semantic Pills Only:** Reserved strictly for eligibility, match tier, requirement status, and grounding pills (`emerald`, `amber`, `rose`, `navy`). Eliminate `indigo-*` and `teal-*`.

## 4. Typography & Numeric Precision
- Headings: `Plus Jakarta Sans` (`font-display`) with tight tracking (`-0.015em`).
- Body & Controls: `Inter` (`font-sans`).
- Numbers, Scores, IDs, DOIs, Page Refs, Confidence, Years & Telemetry: `font-mono tabular-nums` (`JetBrains Mono`) consistently across all views.
