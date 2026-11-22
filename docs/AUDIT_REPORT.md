# FacultyScreen — Full-Stack Functional & Hardcoding Audit Report

**Audit Date**: 2026-11-22  
**Scope**: Full-stack empirical audit of all backend API routes, SQLite database (`42` candidates), `45` processed disk artifacts, domain services/agents, and all Next.js frontend views.

---

## Executive Summary

| Area | Status | Findings |
|---|---|---|
| **Core Extraction & DB Persistence** | Working (with accuracy & dedup flaws) | Real Groq LLM extraction works (`0` mock profiles in DB), `20/20` tests pass, and Next.js builds cleanly. |
| **Frontend Data Fetching & Filtering** | Partially Broken | Global search disconnected, `"Uploaded Only"` filter broken, pagination capped at `50`, silent mock fallbacks hide errors, and extracted extras are dropped. |
| **Analytics & Telemetry** | Mostly Static / Broken | `average_processing_time_sec` hardcoded to `1.8`, `telemetry` counters reset to `0` on restart and stay `0` for uploads, and `needs_review` (`0`) contradicts Review Queue (`1`). |
| **Review Workflow & Re-Screening** | Broken Edge Cases | Low-confidence reviewed candidates stay in Review Queue forever; `POST /api/screening/run` is unwired in UI and wipes manual verdicts; reviews don't sync to disk or refresh analytics. |
| **Classification & Deduplication** | Significant Accuracy Bugs | `64` institution rows (e.g., Carnegie Mellon, UBC, Univ. of San Francisco) misclassified as `State University / Tier 3 / India`; `5` candidates store wrong `highest_degree`; duplicate uploads create up to `6` copies; `11/42` candidates `404` on `/file`. |
| **Hardcoded / Static UI Elements** | Widespread | Static Sidebar cycle info, static Navbar badge/user, hardcoded `Passing: 70.0%`, hardcoded 3-rule matrix in Compare view, and offline mock fallbacks in `api.ts`. |

---

## P0 — Critical Functional Bugs

1. **Frontend Filters, Search, & Sync Broken**:
   - `apps/web/features/candidates/CandidateTable.tsx`: `uploadedOnlyFilter` omitted from `useMemo` dependency array.
   - `apps/web/app/page.tsx`: `globalSearchTerm` never passed from `Navbar` into `CandidateTable`.
   - `apps/web/lib/api.ts`: `fetchCandidates()` omits `limit`, hitting backend default `limit=50`.
   - `apps/web/app/page.tsx`: `handleSyncResumes` waits a fixed `2000ms` timeout instead of polling background job status.
   - `apps/web/components/UploadModal.tsx`: catches upload errors and displays `"Upload completed. Processed locally."`.
2. **Review Queue "Zombie Candidate" Bug & Count Mismatch**:
   - `backend/app/database/repository.py`: `get_review_queue()` includes `confidence < threshold` without excluding `"Manually verified"` / `"Disqualified"`, so reviewed low-confidence candidates reappear forever.
   - `backend/app/api/routes/analytics.py`: `needs_review` count (`0`) disagrees with `GET /api/screening/review-queue` (`1`).
   - `apps/web/features/screening/ReviewQueueView.tsx`: ignores backend `review_reasons`.
   - `apps/web/features/candidates/CandidateDetailView.tsx`: does not reset local `reviewVerdict` / `reviewNotes` when switching candidates.
3. **Extracted Data Dropped Between Disk (`resume.json`) and DB/API (`/api/candidates/{id}`)**:
   - Missing from SQLite/API response: `skills`, `certifications`, `awards`, `projects`, `source_evidence`, `administrative_years`, `research.patents`, `research.research_projects`, `research.research_domains`, `research.books`, `screening.flags`, `screening.decision_path`, `metadata`.
4. **Broken File Streaming (`11/42` `404`s) & Missing PDF Viewer**:
   - Stored absolute paths (`...\Input_resumes\data\uploads\...`) broke after moving `data/uploads/` out of `Input_resumes/`.
   - `CandidateDetailView.tsx` has `'preview'` in `activeCenterTab` type without a viewer, and generates a partial Markdown string client-side instead of showing `resume.md`.
5. **Re-Screening Unwired & Destructive**:
   - `POST /api/screening/run` wipes manual recruiter verdicts/notes and doesn't update `resume.json`/`resume.md`.

---

## P1 — Hardcoded, Static, & Fake / Mocked Items

- **Backend**:
  - `analytics.py`: hardcoded `"average_processing_time_sec": 1.8`; volatile in-memory `jev_router` telemetry; `total_resumes` (33) < `processed` (42).
  - `orchestration_agent.py`: hardcoded `page_count=2`, `groq_api_calls=1`, `jev_decision_calls=rotations_handled`.
  - `jev_router.py`: Tier 3 `"groq_escalation"` never calls Groq.
  - `settings.py`: `PATCH /api/settings/rules` overwrites `version` and `department` with hardcoded values.
  - `extractor.py`: `_generate_realistic_profile_from_file()` silently fabricates synthetic resumes on LLM failure even when `MOCK_MODE=False`.
  - `screening_service.py`: hardcoded rule confidence values, ignores YAML `failure_message`, missing `>`, `<`, `!=`, `contains` operators.
- **Frontend**:
  - `api.ts` + `mockData.ts`: silent mock fallbacks and fake `true` return on failed `submitReview`.
  - `Sidebar.tsx`, `Navbar.tsx`, `CandidateDetailView.tsx`, `CandidateComparisonView.tsx`, `CandidateTable.tsx`, `DashboardOverview.tsx`, `SettingsView.tsx`: static cycle labels, static JEV active badge, hardcoded `70.0%` passing label, hardcoded 3 comparison rules, hardcoded filter dropdowns.

---

## P2 — AI Extraction, Classification & Screening Accuracy Bugs

1. **Institution Catch-All Misclassification**: `InstitutionService._classify_by_heuristics` matched any `"university"`/`"institute"`/`"college"` as `State University / Tier 3 / India` with `0.88` confidence, blocking LLM escalation for `64` entries (including Carnegie Mellon, UBC, Univ. of San Francisco, Univ. of Toronto, Lovely Professional University, Univ. of Allahabad).
2. **Duplicate Candidates on Re-Upload**: `candidate_id` hashed `filename + size` instead of content SHA-256, causing `6` duplicate people in DB (e.g., `SURESH C KESHAV` ×6, `AHMED DAUD AQUIL` ×5).
3. **`education[0]` Assumed Highest Degree**: `5` DB candidates (e.g., `Kenneth Reaves`, `BISHNUPRIYA RAJORIA`) stored `"Other"` or `"Diploma"` as `highest_degree` despite having higher degrees in `education[1:]`.
4. **Tuple-Comparison Bug in `JevDecisions.resolve_degree_level`**: `level = EducationService.normalize_degree(raw_degree)` assigned a `(str, float)` tuple so `level != "Other"` was always `True`, returning `('Other', 0.95)` on unrecognized degrees.
5. **Regex & Date Traps**: Substring keyword matching (`"hod"` inside `"methodology"`, `"m.a"` inside `"pharma"`), `"date"` in `CURRENT_KEYWORDS`, `"dean"`/`"hod"` in `TEACHING_KEYWORDS` before `ADMINISTRATIVE_KEYWORDS`, ungrounded LLM fabrication risk when JSON is truncated or vision-only.

---

## P3 — Architectural & Deployment Gaps

- Dual divergent pipelines (`orchestrator.py` vs `orchestration_agent.py`) and unused `vision_agent.py`.
- `GroqExtractor.is_available` only checks `GROQ_API_KEY` instead of `groq_pool.size`.
- Deprecated FastAPI `@app.on_event("startup")` and Pydantic v2 class-based `Config`.
- Docker config gaps (`next.config.ts` missing `output: "standalone"`, `docker-compose.yml` browser-unresolvable `http://backend:8000`).

---

## Three-Phase Fix Roadmap

- **Phase 1**: Backend data integrity, anti-hallucination grounding & validation (`ValidationService`), pipeline unification, content-hash deduplication, classification/degree/experience accuracy fixes, full DB persistence, and real telemetry.
- **Phase 2**: Review queue zombie fix, analytics parity, non-destructive re-screening & disk sync, full rule operators & YAML `failure_message` support.
- **Phase 3**: Remove all frontend hardcoding & silent mock fallbacks, wire global search/filters/pagination/sync polling, live PDF preview + full extracted profile tabs, dynamic comparison & rules editor.
