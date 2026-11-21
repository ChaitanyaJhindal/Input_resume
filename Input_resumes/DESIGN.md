---
name: FacultyScreen Academic Intelligence
colors:
  surface: '#ffffff'
  surface-dim: '#f8fafc'
  surface-bright: '#ffffff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f8fafc'
  surface-container: '#f1f5f9'
  surface-container-high: '#e2e8f0'
  surface-container-highest: '#cbd5e1'
  on-surface: '#0f172a'
  on-surface-variant: '#475569'
  inverse-surface: '#0f172a'
  inverse-on-surface: '#f8fafc'
  outline: '#cbd5e1'
  outline-variant: '#e2e8f0'
  primary: '#1e3a8a'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eff6ff'
  secondary: '#059669'
  on-secondary: '#ffffff'
  secondary-container: '#ecfdf5'
  on-secondary-container: '#065f46'
  tertiary: '#d97706'
  on-tertiary: '#ffffff'
  tertiary-container: '#fffbeb'
  on-tertiary-container: '#92400e'
  error: '#dc2626'
  on-error: '#ffffff'
  error-container: '#fef2f2'
  on-error-container: '#991b1b'
  background: '#f8fafc'
  on-background: '#0f172a'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 22px
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-lg:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.03em
  data-metric:
    fontFamily: JetBrains Mono
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  data-tabular:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.375rem
  md: 0.5rem
  lg: 0.75rem
  xl: 1rem
  full: 9999px
spacing:
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-base: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  gutter: 1.5rem
---

# FacultyScreen Design System

## 1. Brand & Design Philosophy
FacultyScreen is a high-precision, decision-support platform designed for university recruitment committees, deans, and academic search chairs. The interface exudes academic authority, empirical clarity, and operational efficiency. It rejects neon "AI startup" gimmicks, excessive gradients, cartoon avatars, and opaque scoring meters in favor of crisp typography, structural borders, compact data tables, and transparent evidence trails.

## 2. Color Palette & Semantics
- **Canvas Base:** `#f8fafc` (Slate 50) - Neutral substrate providing high contrast without starkness.
- **Card & Surface Background:** `#ffffff` (Pure White) - Crisp boundaries for inspection panels and data tables.
- **Primary Accent:** `#1e3a8a` (Collegiate Navy) & `#2563eb` (Cobalt) - Reserved for active navigation, primary action buttons, and active filter states.
- **Semantic Status Signals:**
  - **Eligible / Verified / High Confidence:** `#059669` (Emerald 600) with `#ecfdf5` background and `#a7f3d0` border.
  - **Needs Review / Ambiguous:** `#d97706` (Amber 600) with `#fffbeb` background and `#fde68a` border.
  - **Ineligible / Disqualified:** `#dc2626` (Red 600) with `#fef2f2` background and `#fecaca` border.
  - **Informational / Metadata:** `#0284c7` (Sky 600) with `#f0f9ff` background and `#bae6fd` border.
- **Borders & Partitions:** `#e2e8f0` (Slate 200) for standard 1px structural borders; `#cbd5e1` (Slate 300) for hover and active controls.

## 3. Typography
- **Headings & Titles (Plus Jakarta Sans):** Modern geometric clarity for page titles, modal headers, and candidate names.
- **Body & Controls (Inter):** Neutral, highly legible sans-serif for narrative summaries, employment timelines, and metadata.
- **Numerical & Extracted Evidence (JetBrains Mono):** Precision monospaced font for years of experience, publication counts, DOI strings, and raw source text snippets.

## 4. UI Components

### Tables & Data Density
- Compact 40px row height with subtle zebra striping (`#f8fafc` on alternating rows).
- Column headers in uppercase `label-sm` with active sort glyphs.
- Candidate quick badges: Highest Degree pill, Normalized Institution category tag, and Experience breakdown (Teaching | Industry | Research).
- Sticky header and row hover highlight (`#f1f5f9`).

### Candidate Detail Tri-Pane Layout
- **Left Column (280px):** Candidate avatar initials, contact coordinates, quick metadata, eligibility badge, and verification status action buttons.
- **Center Column (Fluid 60%):** Extracted resume facts presented in structured sections (Education with Degree Normalization, Timeline-ordered Experience, Research & Publications with DOIs, Certifications & Skills).
- **Right Column (380px):** AI Screening & Evidence Panel showing rule-by-rule pass/fail evaluation, confidence meters, JEV routing traces, and exact source snippet quotes with page numbers.

### Buttons & Interactive Controls
- **Primary Action:** Solid `#1e3a8a` fill with white text, 6px radius, hover state `#172554`.
- **Secondary / Outline:** `#ffffff` surface, 1px border `#e2e8f0`, hover state `#f8fafc`.
- **Filter Chips:** 26px height, rounded-full, 1px border `#cbd5e1`, with active count indicators.
