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
- **Status**: Pending
- **What will be built**:
  - 7-stage tailoring orchestrator: JD analysis, Technique selection, Gap analysis, Targeted rewrite, Impact pass, Truthfulness check, and Rendering.
  - LLM routing logic: Gemini 3.5 Flash as standard model, escalating to Gemini 3.1 Pro/3.5 Pro for the Impact pass and Truthfulness check.
  - Validation retry decorator for backend LLM calls.
  - UI interface displaying gap analysis results, suggested rewrites, and the Truthfulness Gate approval prompt.
