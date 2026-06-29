# Project Progress Log

## Phase 0: Scaffold & Schema
- **Status**: Completed & Verified
- **Date**: 2026-06-28
- **What was built**:
  - Root workspace configurations: `.gitignore`, `.env`, and `.env.example`.
  - Supabase database initialization migrations with `pgvector` and tables: `users`, `profiles`, `jobs`, `applications`, `tailored_resumes`, `technique_library`, `job_cache`.
  - FastAPI backend skeleton with configuration loader, health-check, echo routing, and typed schemas.
  - Next.js frontend skeleton with landing page verification UI, TypeScript, Tailwind, and Vitest configuration.
- **Verification**:
  - Backend tests run and passed (`pytest backend/tests/test_health.py` and `pytest backend/tests/test_database.py`), confirming health, echo routing, and the unique constraint on the applications table.
  - Frontend unit tests run and passed (`npm run test`).
  - CI pipeline configuration added and verified under `.github/workflows/ci.yml`.
- **Decisions**:
  - Standardized embedding vector dimensions to **768** to align with Gemini's default `text-embedding-004` model.
  - Initialized both FastAPI and Vitest test suites to prevent contract regression during subsequent phases.
  - Resolved psycopg connection string parsing error by passing `connect_timeout` directly to the `psycopg.connect` kwargs rather than string concatenation on a URI.
  - Implemented typed API endpoints stubs (`/tailor`, `/jobs/search`, `/apply/draft`, `/apply/submit`) to establish a complete contract skeleton between frontend and backend.

---

## Phase 1: Resume Core
- **Status**: Completed & Verified
- **Date**: 2026-06-28
- **What was built**:
  - PDF text and layout block coordinate parser using PyMuPDF.
  - OCR fallback logic using pytesseract / PIL to catch scanned PDF edge cases.
  - Self-correcting schema validation LLM extractor using Gemini 3.5 Flash that corrects validation errors over multiple retry runs.
  - GitHub REST API profile enricher that aggregates language statistics and stars with rate limit/404 fallbacks.
  - Document compilers for both high-fidelity PDF (via WeasyPrint) and ATS-optimized Word (via python-docx) documents.
  - Frontend Drag-and-Drop file intake component and tabbed candidate profile viewer with download triggers.
- **Verification**:
  - Backend unit and integration tests run and passed (`pytest backend/tests/test_resume_core.py`).
  - E2E browser subagent verified frontend-backend health, serialization, and page rendering (`phase_1_verification.webp`).
- **Decisions**:
  - Enforced a minimum text layer limit of 100 characters to trigger OCR fallback for scanned/empty resume uploads.
  - Captured both `ImportError` and `OSError` to identify missing platform libraries (like Windows GTK+ for WeasyPrint) and output clean error messages rather than raw application crashes.

---

## Phase 2: Tailoring Pipeline & Technique Library
- **Status**: Completed & Verified
- **Date**: 2026-06-28
- **What was built**:
  - Extended Pydantic schemas in `backend/app/schemas.py` supporting all intermediate tailoring stage data transfers.
  - Implemented all 7 pipeline stages: JD Analysis (Stage 1), Technique Selection with SQL fallback (Stage 2), Gap Analysis (Stage 3), Targeted Factual Rewrite (Stage 4), Impact Pass & Density Trimming (Stage 5), Truthfulness Gate auditing (Stage 6), and Compile (Stage 7).
  - Built the tailoring sequence orchestrator `backend/app/pipeline/orchestrator.py` and connected it to the FastAPI `/tailor` endpoint.
  - Updated PDF and Word document compilers to render the tailored tagline (anchor line) and relevance highlights.
  - Created glassmorphic frontend `TailorPanel.tsx` for pasting job listings and displaying step progression.
  - Created interactive frontend `TruthfulnessGate.tsx` displaying ATS match scores, honest skill gaps, fabrication flags, and inline bullet editors.
- **Verification**:
  - Backend integration tests authored in `backend/tests/test_tailor_pipeline.py` covering sequential runs, prompt injection safety, short JDs, database offline fallbacks, and truthfulness alerts.
  - Frontend type safety type-checked via `npx tsc --noEmit` and tests executed with 100% pass counts.
- **Decisions**:
  - Implemented sequence-based mocking of the shared `llm_client.generate_structured` singleton method to prevent test cross-contamination in pytest.
  - Designed `/tailor` endpoint request payload to allow optional parsed resume data, permitting fully operational, database-less execution paths.
  - Set default density control bounds to restrict experiences to at most 3 bullets per job and 8 total bullets, prioritizing the highest-impact metrics first to ensure single-page layouts.

---

## Phase 3: Job Search, Aggregation, Caching, and Matching
- **Status**: Completed & Verified
- **Date**: 2026-06-29
- **What was built**:
  - Unified Job Aggregator Service in `backend/app/services/job_service.py` to query JSearch, Jooble, Remotive, and Arbeitnow concurrently with async semaphores.
  - Hash-based job deduplication (`job_hash` via SHA-256 over normalized title, company, location).
  - Multi-criteria matching engine (keyword overlap, title match, location alignment, and recency) with match explanation generation.
  - Dual-tier caching (Postgres database cache table with automatic fallback to in-memory `IN_MEMORY_JOB_CACHE` if DB is unreachable).
  - Applied-status indicators displaying checkmarks for jobs the candidate already applied to.
  - Interactive glassmorphic search dashboard component `JobSearch.tsx` with limit, keywords, and remote filters.
  - Integrated "Tailor Resume" action in search results to auto-navigate to the tailoring tab with pre-filled job descriptions.
- **Verification**:
  - Backend automated unit and integration tests added in `backend/tests/test_jobs.py` (caching, score math, deduplication, remote filtering, applied checks).
  - Full backend test suite executed and passed (27 passed, 1 skipped).
  - E2E manual walkthrough and screenshots captured on port 3005 dev server.
- **Decisions**:
  - Added support for database-less fallback where listings are assigned transient UUIDs if Postgres is offline, ensuring the user experience never crashes.
  - Integrated the Jobs tab directly alongside Experience/Skills tabs on the profile dashboard, optimizing navigation hierarchy.
  - Modified CORS configurations to support frontend port 3005 to permit development and verification sandboxing.

