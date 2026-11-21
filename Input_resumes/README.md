# FacultyScreen — AI Professor Resume Screening & Curation Platform

**FacultyScreen** is a production-quality, decision-support platform engineered for universities, academic recruitment committees, and college deans to autonomously screen, extract, normalize, and curate professor resumes with **100% explainable evidence**.

---

## 🏛️ System Architecture

```
                  [Resume Upload / Existing Resumes Folder]
                                      │
                                      ▼
                        [File Detection & Ingestion]
                         - Scans PDF / PNG / JPG / JPEG
                         - Computes SHA-256 Checksum
                         - Stable Candidate ID (cand_...)
                         - Originals NEVER mutated or renamed
                                      │
                                      ▼
                   [Multimodal Document Understanding]
                    - pypdfium2 In-Memory Page Rendering
                    - Groq Vision API (qwen/qwen3.8-27b)
                    - Structured JSON Fact Extraction
                    - Traceable Source Quotes & Page Numbers
                                      │
                                      ▼
                     [Three-Tier Decision Hierarchy]
                     1. Deterministic Local Database (0ms)
                     2. TypeSafe AI / JEV Structured Decisions
                     3. Groq LLM Escalation (Ambiguous Only)
                                      │
                                      ▼
                  [Academic Standardization & Normalization]
                    - EducationService (PhD, Masters, UG)
                    - InstitutionService (IIT, NIT, Central, State, Private, Intl)
                    - ExperienceService (Non-Overlapping Teaching/Research/Industry)
                    - ResearchService (Publications, Venues, DOIs, Patents)
                                      │
                                      ▼
                        [Configurable Screening Engine]
                      - config/screening_rules.yaml
                      - Mandatory vs Preferred Requirements
                      - Weighted Scoring (0-100%) & Confidence Floor
                      - Transparent Reason & Evidence per Rule
                                      │
                                      ▼
                        [Persistence & Output Artifacts]
                     data/processed/{candidate_id}/
                       ├── original_reference.json
                       ├── resume.json (Canonical Machine-Readable)
                       ├── resume.md (Human-Readable Context)
                       └── metadata.json
                     data/facultyscreen.db (SQLAlchemy / PostgreSQL)
                                      │
                                      ▼
                    [Enterprise Recruiter Dashboard]
                     - Next.js 16 + React 19 + Tailwind CSS
                     - Google Stitch Design System Adherence
                     - Tri-Pane Candidate Detail Inspection
                     - Human Review Queue & Candidate Comparison
```

---

## 🌟 Key Features

1. **Multimodal Visual Document Understanding**:
   - Leverages **Groq Qwen Vision (`qwen/qwen3.8-27b`)** to parse multi-column, scanned, and tabular academic resumes without OCR hallucination.
   - Extracts exact verbatim evidence quotes with source page references for every degree, institution, and publication.

2. **Deterministic Experience Calculation**:
   - Disaggregates total career duration into:
     - **Teaching Experience** (Professorships, Lectureships, Instructorships)
     - **Research Experience** (Postdoctoral fellowships, Scientist appointments)
     - **Industry Experience** (Corporate R&D, Software engineering)
     - **Administrative Experience** (Dean, HOD, Director appointments)
   - Merges concurrent/overlapping intervals to mathematically prevent double-counting.

3. **Three-Tier Fast Decision Architecture (JEV / TypeSafe AI)**:
   - **Tier 1 (Deterministic)**: Checks local institutional taxonomy (`data/institutions/institutions.json`) for instant <1ms lookup.
   - **Tier 2 (JEV Fast Layer)**: Routes classification edge cases and structured boolean decisions to TypeSafe AI without long-form LLM overhead.
   - **Tier 3 (Groq Escalation)**: Only escalates to full LLM reasoning when ambiguity remains unresolved.

4. **Zero-Pollution Ingestion**:
   - Reads directly from the source-of-truth directory configured by `RESUMES_DIR`.
   - Never renames, moves, overwrites, or deletes original PDF documents.
   - Saves all artifacts into isolated `data/processed/{candidate_id}/` directories.

5. **Decision Support (Never an Opaque Score)**:
   - Hiring rules are defined in `config/screening_rules.yaml` (Doctoral requirement, minimum teaching years, publication counts).
   - Every candidate evaluation outputs the exact rule name, status (Pass/Fail), explanation, and source quote.

6. **Google Stitch Enterprise UI**:
   - Built to match Google Stitch design tokens: Collegiate Navy (`#1e3a8a`), Emerald (`#059669`), Amber (`#d97706`), and Slate (`#f8fafc`).
   - Includes:
     - **Overview Dashboard**: Key recruitment KPIs, degree & institutional distribution charts.
     - **Resume Library**: Dense data table with multi-faceted filtering, sorting, and density controls.
     - **Candidate Detail Tri-Pane**: Left identity & stats, Center extracted tabs & Markdown, Right AI screening panel with recruiter audit actions.
     - **Human Review Queue**: Candidates flagged due to low confidence or borderline qualifications with explicit triggers.
     - **Compare Candidates**: Side-by-side comparison matrix for 2 to 4 candidates.
     - **Analytics**: Deep-dive charts and JEV vs LLM telemetry.
     - **Settings**: Interactive screening rules editor and taxonomy browser.

---

## 🚀 Quick Start & Setup

### Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Node.js 18+ (Node v20/v25 recommended) & npm

### 1. Clone & Set Up Python Environment
```bash
# Clone the repository
git clone <repo-url>
cd Input_resumes

# Create clean virtual environment
python -m venv .venv
.venv\Scripts\activate   # On Windows
# source .venv/bin/activate  # On Linux/macOS

# Install dependencies
pip install -r backend/requirements.txt
# Or using uv for ultra-fast installation:
# uv pip install -r backend/requirements.txt
```

### 2. Configure Environment (`.env`)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Review the parameters in `.env`:
```ini
# Application Mode
ENVIRONMENT=development
DEBUG=True
MOCK_MODE=False

# Host & Ports
HOST=127.0.0.1
PORT=8000
FRONTEND_PORT=3000

# Path to existing resumes directory (Source of Truth)
RESUMES_DIR=.

# Groq Vision Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_VISION_MODEL=qwen/qwen3.8-27b
GROQ_MAX_TOKENS=900
GROQ_TEMPERATURE=0.2

# TypeSafe AI / JEV Configuration
TYPESAFE_API_KEY=
JEV_MODEL=jev-v1-fast
TYPESAFE_BASE_URL=https://api.typesafe.ai

# Database
DATABASE_URL=sqlite:///./data/facultyscreen.db

# Frontend API URL
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

> **Note on Mock Mode**: The system functions completely out-of-the-box even **without API keys**. If `GROQ_API_KEY` is empty, the system automatically runs with `MOCK_MODE=True`, producing realistic academic profiles and full interactive UI functionality.

---

### 3. Run Backend (FastAPI)
```bash
# Start FastAPI backend with hot-reload
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### 4. Run Frontend (Next.js)
In a separate terminal:
```bash
cd apps/web
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser to access the Recruiter Dashboard.

---

## 🧪 Testing

Run the full automated test suite (unit and API integration tests):

```bash
# Run all unit tests
python -m pytest tests/unit/test_engine.py

# Run all API integration tests
python -m pytest tests/integration/test_api.py

# Run all tests with coverage
python -m pytest tests/
```

---

## 📂 Clean Project Structure

```
Input_resumes/
│
├── apps/web/                              # Modern Next.js 16 Frontend
│   ├── app/                               # Next.js App Router (layout, page, styles)
│   ├── components/                        # Shared UI (Navbar, Sidebar, UploadModal)
│   ├── features/                          # Intuitive feature modules:
│   │   ├── dashboard/                     # Overview KPIs & summary stats
│   │   ├── candidates/                    # Candidate library & tri-pane inspection
│   │   ├── screening/                     # Review queue & manual verification
│   │   ├── comparison/                    # Side-by-side comparison matrix (2-4 candidates)
│   │   ├── analytics/                     # Pipeline metrics & JEV telemetry
│   │   └── settings/                      # Configurable screening rules editor
│   ├── lib/api.ts                         # Typed REST API client
│   └── types/candidate.ts                 # TypeScript data models
│
├── backend/app/                           # Clean FastAPI Backend
│   ├── agents/                            # 7 Specialized AI Screening Agents:
│   │   ├── orchestration_agent.py         # Master pipeline coordinator
│   │   ├── vision_agent.py                # Visual OCR & multimodal parser
│   │   ├── education_agent.py             # Degree extraction & hierarchy normalization
│   │   ├── experience_agent.py            # Teaching/Research/Industry tenure disaggregator
│   │   ├── institution_agent.py           # Institution categorization & NIRF/NAAC tiering
│   │   ├── research_agent.py              # Publications & citations indexing
│   │   └── screening_agent.py             # YAML rules evaluation & weighted scoring
│   ├── api/routes/                        # REST API Endpoints:
│   │   ├── candidates.py                  # Search, filter, compare, review, delete
│   │   ├── resumes.py                     # Upload PDF, status stream, process
│   │   ├── screening.py                   # Screening queue & criteria
│   │   ├── analytics.py                   # Dashboard statistics & breakdown
│   │   └── settings.py                    # Screening rules & key telemetry
│   ├── database/                          # Relational Storage (SQLite / PostgreSQL):
│   │   ├── models.py                      # SQLAlchemy models (Candidate, Education, etc.)
│   │   └── repository.py                  # Clean data repository (CRUD, query, delete)
│   ├── groq/                              # Groq AI Layer:
│   │   ├── pool.py                        # Distributed Round-Robin Key Pool (auto-429 failover)
│   │   └── extractor.py                   # Multi-page text & vision fact extraction
│   ├── config.py                          # Centralized settings & .env parser
│   ├── main.py                            # FastAPI app entry point & CORS configuration
│   ├── schemas/resume.py                  # Pydantic schemas & validation
│   ├── services/                          # Business logic & domain standardizers
│   └── utils/markdown_generator.py        # Generates clean human-readable Markdown
│
├── config/                                # System Configuration (YAML):
│   ├── app_config.yaml                    # System taxonomies & degree hierarchies
│   └── screening_rules.yaml               # Configurable academic screening rules
│
├── data/                                  # Data Storage & Outputs:
│   ├── processed/{candidate_id}/          # Generated facts & resume.json per candidate
│   └── facultyscreen.db                   # SQLite relational database
│
├── docs/                                  # Documentation:
│   ├── architecture.md                    # System architecture & decision tiers
│   ├── decisions.md                       # Architectural decisions & rationale
│   └── extraction-schema.md               # JSON schema specification
│
├── tests/                                 # Test Suite:
│   ├── integration/test_api.py            # API endpoint integration tests
│   └── unit/                              # Unit tests for scoring & decision layer
│
├── .env                                   # Environment keys (Groq, Ports, DB)
├── run_facultyscreen.bat                  # One-click launcher (starts backend + frontend)
├── stop_facultyscreen.bat                 # One-click shutdown for background servers
└── README.md                              # Complete system documentation
```

---

## 🔧 Screening Rule Configuration

Screening rules are stored in `config/screening_rules.yaml`. You can customize hiring criteria dynamically through the UI Settings or directly in YAML:

```yaml
version: "1.0.0"
department: "General Faculty Pool"

rules:
  - id: "RULE_MIN_DEGREE"
    name: "Doctoral Degree Requirement"
    field: "education.highest_degree"
    operator: "in"
    required_value: ["PhD / Doctorate", "Postdoctoral"]
    is_mandatory: true
    weight: 30
    failure_message: "Candidate does not possess an earned Doctorate/Ph.D. degree."

  - id: "RULE_MIN_TEACHING_EXP"
    name: "Minimum Teaching Experience"
    field: "experience.teaching_years"
    operator: ">="
    required_value: 2.0
    is_mandatory: true
    weight: 25

  - id: "RULE_MIN_PUBLICATIONS"
    name: "Scholarly Publications"
    field: "research.publications_count"
    operator: ">="
    required_value: 2
    is_mandatory: true
    weight: 20

settings:
  overall_passing_score_percentage: 70.0
  minimum_confidence_for_auto_approval: 0.85
  needs_review_confidence_floor: 0.65
```

---

## 🛡️ Security & Privacy
- **Source Protection**: The original resumes in `RESUMES_DIR` are mounted read-only and never modified.
- **No Client Secrets**: Neither `GROQ_API_KEY` nor `TYPESAFE_API_KEY` are ever exposed to the client browser.
- **Path Traversal Prevention**: File access is strictly bound to validated deterministic candidate IDs.

---

## 🚢 Docker Deployment
To launch the entire platform in production containers:
```bash
docker compose up -d --build
```
This builds and starts the FastAPI backend on `:8000` and the Next.js frontend on `:3000`.
