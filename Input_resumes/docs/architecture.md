# FacultyScreen - System Architecture

FacultyScreen is an enterprise-grade AI-powered professor resume screening and curation platform designed for university recruitment committees and academic deans.

```
[Resume Upload / Existing Resumes Folder]
                   │
                   ▼
       [File Detection & Ingestion]
        - PDF / PNG / JPG Support
        - SHA-256 Checksum Hashing
        - Stable Candidate ID Assignment
                   │
                   ▼
  [Multimodal Document Understanding]
   - pypdfium2 PDF Page Rasterizer
   - Groq Vision API (qwen/qwen3.8-27b)
   - Structured JSON Fact Extraction
   - Null-Safe Absence Representation
                   │
                   ▼
    [Three-Tier Decision Hierarchy]
    1. Deterministic Rule Matching (Local Taxonomy)
    2. JEV / TypeSafe AI Fast Structured Decisions
    3. Groq LLM Escalation (Ambiguous Cases Only)
                   │
                   ▼
 [Academic Standardization & Normalization]
   - EducationService (PhD, Masters, UG)
   - InstitutionService (IIT, NIT, Central, State, Private, Intl)
   - ExperienceService (Non-Overlapping Teaching/Research/Industry)
   - ResearchService (Publications, Venues, DOIs, Patents)
                   │
                   ▼
       [Configurable Rule Engine]
     - config/screening_rules.yaml
     - Mandatory vs Preferred Requirements
     - Weighted Scoring & Passing Threshold
     - Traceable Evidence Quotes & Page Numbers
                   │
                   ▼
       [Persistence & Artifacts]
    data/processed/{candidate_id}/
      ├── original_reference.json
      ├── resume.json (Canonical)
      ├── resume.md (Human-Readable)
      └── metadata.json
    data/facultyscreen.db (SQLAlchemy / PostgreSQL)
                   │
                   ▼
   [Enterprise Decision-Support UI]
    - Next.js 16 + React 19 + Tailwind CSS
    - Google Stitch Design System Compliant
    - Tri-Pane Candidate Detail View
    - Screening Queue & Multi-Candidate Compare
```

## Three-Tier Decision Strategy
1. **Tier 1 - Deterministic Code & Database**: Resolves >85% of institutional names and degree aliases in <1ms without token consumption.
2. **Tier 2 - JEV / TypeSafe AI Layer**: Evaluates structured rule conditions, classification edge cases, and confidence thresholds at sub-second speeds.
3. **Tier 3 - Groq Qwen Vision**: Reserved strictly for raw multimodal visual document OCR and visual layout understanding.

## Explainability Contract
- Source evidence quotes and page numbers are preserved for every extracted credential.
- No opaque AI scores: every screening score is a transparent weighted sum of explicit rule evaluations.
