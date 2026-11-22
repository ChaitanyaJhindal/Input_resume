# Architectural Decisions & Rationales (ADRs)

## 1. Preserving Source-of-Truth Resume Directory
- **Decision**: Read resumes directly from the read-only source folder configured by `RESUMES_DIR=./Input_resumes` without copying, moving, or modifying any existing PDF/image files.
- **Rationale**: Universities store resumes across pre-existing file systems or network shares. Generating artifacts separately into `data/processed/{candidate_id}/` ensures idempotency, data safety, and zero pollution of input documents.

## 2. In-Memory Page Rendering & Base64 Multimodal Payload
- **Decision**: Use `pypdfium2` to render PDF pages directly to in-memory JPEG buffers and encode as `data:image/jpeg;base64,...` data URLs.
- **Rationale**: External document URLs often trigger HTTP 403 bot blocks (e.g. Wikimedia/cloud buckets). In-memory rendering ensures 100% reliable document delivery to Groq Vision `qwen/qwen3.8-27b`.

## 3. Deterministic Non-Overlapping Experience Calculation
- **Decision**: Parse start and end date intervals, classify roles by keywords into `teaching`, `research`, `industry`, and `administrative`, and merge overlapping intervals.
- **Rationale**: Many candidates hold simultaneous concurrent appointments (e.g., adjunct lecturer + corporate consultant, or PhD fellow + lab assistant). Simple summation inflates career duration. Interval merging prevents double-counting.

## 4. JEV / TypeSafe AI Service Abstraction
- **Decision**: Encapsulate JEV behind `JevClient` and `JevRouter` with graceful fallback to deterministic logic when API keys are not supplied.
- **Rationale**: High resilience. The system operates fully in mock/development environments without vendor lock-in or network failure vulnerability.

## 5. Google Stitch Design System Adherence
- **Decision**: Use Collegiate Navy (`#1e3a8a`), crisp Slate backgrounds (`#f8fafc`), and high-density academic tables rather than generic SaaS cards or neon startup gradients.
- **Rationale**: Academic search committees require high information density, rapid scanning, and professional institutional atmosphere.
