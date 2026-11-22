# FacultyScreen — Agentic System & Full-Stack Production Audit Report

**Audit Date:** 2026-11-22  
**Scope:** Multi-agent orchestration pipeline, Groq LLM pool & extractor, JEV hybrid router/decisions, domain services (education, institution, experience, research, validation, screening), SQLite repository & FastAPI routes, modular YAML configuration manager, and Next.js frontend API contracts.

---

## Executive Summary

While Phase 1–3 resolved database hydration bugs, anti-hallucination verification on text extraction, rule operators, and initial UI polish, a deep production audit across the **entire agentic architecture and full-stack boundary** uncovered **4 Critical**, **7 High**, and **5 Medium** severity defects:

- **UI ↔ Config Schema Divergence (C1):** The Settings UI edited nested `providers.groq` / `providers.jev` keys and nonexistent `app_config` / `prompts` fields, while the backend stored top-level `groq` / `jev` and different task/prompt keys. Without backend validation, saving from the UI could overwrite `config/llm_config.yaml` and break every LLM agent at runtime.
- **Upload Batch Response Mismatch (C2):** `UploadModal.tsx` read `cand.score`, `cand.eligibility`, and `errItem.filename`, whereas `POST /api/resumes/upload-batch` returned `overall_score`, `eligibility_status`, and `file` — causing a runtime `TypeError` (`cand.score.toFixed`) on every batch upload, plus `.webp` upload acceptance mismatch.
- **Path Traversal & Unsafe Input Handling (C3):** Untrusted `candidate_id` values in routes and `CandidateRepository` were joined directly into filesystem paths (including `shutil.rmtree` in `delete_candidate`), and upload filenames were not stripped of directory components.
- **Disconnected Agentic Architecture (C4):** `JevRouter` was bypassed by every active agent (`jev_decision_calls=0` hardcoded in `orchestration_agent.py`), `ExperienceAgent` LLM calls/escalations were untracked, `VisionAgent` was duplicated dead code using raw `json.loads`, and `JevClient._local_fallback` contained unguarded substring bugs (`"ms"`, `"be"`, `"university" -> State University`) while returning `confidence=0.92, is_escalated=False` for `"Other"`.

All findings below have been remediated with production-grade code and verified by automated unit and integration tests.

---

## Findings Matrix

### Critical Findings

| ID | Component & Location | Root Cause | Remediation |
| :--- | :--- | :--- | :--- |
| **C1** | `apps/web/types/candidate.ts`, `apps/web/features/settings/SettingsView.tsx`, `backend/app/config_manager.py`, `backend/app/api/routes/settings.py` | Frontend edited `providers.groq`/`providers.jev`, omitted half the keys in `prompts.yaml` (`text_system`, `extraction_instructions`, `user_template`, `prompt`), and edited wrong keys under `pipeline.*`. `ConfigManager` wrote raw unvalidated dicts to YAML. | Aligned frontend TypeScript interfaces and `SettingsView.tsx` sub-tabs to exact `llm_config.yaml`, `prompts.yaml`, and `app_config.yaml` schemas; added strict YAML schema validation + atomic writes in `ConfigManager` and HTTP 400 validation in `settings.py`. |
| **C2** | `apps/web/components/UploadModal.tsx`, `apps/web/lib/api.ts`, `backend/app/api/routes/resumes.py` | `UploadBatchResult` expected `score`, `eligibility`, and `errors[].filename` while backend returned `overall_score`, `eligibility_status`, and `errors[].file`; `.webp` accepted in UI modal was missing from `config/app_config.yaml`. | Updated `UploadModal.tsx` & `api.ts` to match exact backend contract, added `.webp` to `app_config.yaml` and `VisionAgent`, and included both `filename` and `file` in backend error entries. |
| **C3** | `backend/app/api/routes/{resumes,candidates,screening}.py`, `backend/app/database/repository.py`, `backend/app/utils/json_utils.py` | `candidate_id` path parameters were concatenated directly onto `processed_dir` and passed to file reads, writes, and `shutil.rmtree`; `file.filename` in uploads used `Path(file.filename)` without directory stripping. | Added `validate_candidate_id` (`^[A-Za-z0-9_-]{4,64}$`), `safe_child_path` (`is_relative_to` enforcement), and `sanitize_filename` across repository and all routes. |
| **C4** | `backend/app/services/jev/{jev_client,jev_router}.py`, `backend/app/agents/{education,institution,experience,vision,orchestration}_agent.py` | Agents bypassed `jev_router`; `ExperienceAgent` LLM usage wasn't counted in telemetry; `VisionAgent` was unused duplicate code; `JevClient._local_fallback` duplicated stale regex/substring bugs (`"ms"`, `"be"`, `"university"` -> State University, `"Other"` -> 0.92). | Unified all three classification agents (`EducationAgent`, `InstitutionAgent`, `ExperienceAgent`) onto `jev_router.route_decision(...)`; eliminated stale rules in `JevClient._local_fallback` by delegating to curated services with truthful escalation flags; unified Vision rendering/extraction through `VisionAgent` and aggregated complete telemetry (`det`, `jev`, `groq`, `esc`). |

---

### High Severity Findings

| ID | Component & Location | Root Cause | Remediation |
| :--- | :--- | :--- | :--- |
| **H1** | `backend/app/agents/{orchestration,education,institution,experience,vision}_agent.py`, `backend/app/services/research_service.py` | Direct `float()`, `int()`, raw `json.loads()`, unvalidated LLM categories, `null` list crashes (`raw_facts.get("skills", [])` when key exists with `None`), and `ResearchService.detect_indexing` matching `"sci"` inside `"computer science"`. | Created shared defensive helpers (`safe_int`, `safe_float`, `safe_str_list`, `safe_dict_list`), validated all agent LLM enums against configured taxonomies, clamped confidences to `[0.0, 1.0]`, and fixed `detect_indexing` with `\b...\b` word boundaries + publication deduplication. |
| **H2** | `backend/app/agents/orchestration_agent.py`, `backend/app/groq/extractor.py` | `ProcessingMetadata.model_name` hardcoded `resolve_model("vision")` even when Stage 2 text LLM (`openai/gpt-oss-20b`) performed extraction. | `GroqExtractor` records `"_model_used"` accurately for text, vision, mock, and failure paths; `OrchestrationAgent` persists `raw_facts.get("_model_used")`. |
| **H3** | `backend/app/services/experience_service.py`, `backend/app/agents/experience_agent.py` | Every industry job escalated to Groq LLM; `parse_date_decimal` failed on numeric dates (`06/2020`, `2020-07`) and 2000–2019 2-digit years (`May-18`); `parse_date_range` ignored `is_current=True`; `"Director of Engineering"` misclassified as academic admin. | Added `INDUSTRY_KEYWORDS` + `categorize_employment_with_confidence`, protected corporate executive titles in industry context, added numeric month and `00–29` 2-digit year parsing, and handled `is_current=True` with empty `end_date`. |
| **H4** | `backend/app/groq/extractor.py`, `backend/app/utils/json_utils.py` | Bracket counter for truncated JSON ignored string literals (braces inside strings) and appended all `]` before all `}` instead of preserving LIFO nesting; Stage 2 text prompt omitted `response_format={"type": "json_object"}`. | Implemented string-aware LIFO stack JSON repair in `parse_llm_json`; added `response_format={"type": "json_object"}` on Stage 2 text calls with automatic single retry without `response_format` if rejected by an upstream model. |
| **H5** | `backend/app/services/validation_service.py` | Placeholder strings survived inside `evidence` fields; negative durations passed unguarded; `source_evidence` quotes were unverified; text-rich PDFs with zero extracted items received `grounding_score=1.0`; duplicate employment/publication rows were kept. | Cleaned evidence placeholders, clamped negative durations, deduplicated employment/publications, normalized whitespace for email lookup, grounded `source_evidence`, and capped `grounding_score=0.50` when text-rich PDFs yield zero extractable claims. |
| **H6** | `backend/app/groq/pool.py`, `backend/app/services/{jev/jev_router,screening_service}.py`, `backend/app/database/models.py` | `GroqKeyPool` slept inside `self._lock`, logged partial secrets (`self.key[:10]`), had no SDK timeout, and dropped transient 5xx/timeouts; `JevRouter.stats` and `ScreeningService` lacked thread locks; SQLite lacked WAL/`busy_timeout`; writes were non-atomic. | Released lock before sleeping in `GroqKeyPool`, sanitized logs, added request `timeout`, `Retry-After` handling, and transient 5xx/timeout retries; added `RLock`/`Lock` to `JevRouter` & `ScreeningService`; enabled SQLite `WAL` + `busy_timeout=5000`; used atomic temp-file writes (`os.replace`) everywhere. |
| **H7** | `backend/app/api/routes/{candidates,screening,resumes}.py`, `backend/app/main.py` | Unvalidated `verdict` silently disqualified unknown strings; unvalidated `sort_by` caused `getattr` 500s; `screening/run` crashed when `metadata` was `None` and stopped at 1000 rows; uploads lacked size/empty guards; `allow_origins=["*"]` paired with `allow_credentials=True`. | Enforced `Literal` verdicts, `sort_by` column whitelist, unbounded ID iteration + null-safe metadata in `screening/run`, upload empty/max-MB guards, configurable `cors_origins`, structured `logger` calls, and timezone-aware UTC timestamps. |

---

## Medium Findings Addressed
- **M1:** Replaced deprecated `datetime.utcnow` across SQLAlchemy models and `OrchestrationAgent` with timezone-aware `datetime.now(timezone.utc)`.
- **M2:** Replaced bare `print()` diagnostics in `CandidateRepository`, `resumes.py`, and `InstitutionService` with module loggers.
- **M3:** Recomputed `ExperienceBreakdown` in `OrchestrationAgent` if `ValidationService` removes duplicate employment records so totals match deduplicated roles.
- **M4:** Supported `.webp` uploads end-to-end by normalizing images to JPEG via Pillow in `VisionAgent`.
- **M5:** Enforced case-insensitive JSON repair dict checks so array/scalar LLM outputs cannot masquerade as extracted profile dicts.
