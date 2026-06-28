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
  - Backend tests run and passed (`pytest backend/tests/test_health.py`).
  - Frontend unit tests run and passed (`npm run test`).
- **Decisions**:
  - Standardized embedding vector dimensions to **768** to align with Gemini's default `text-embedding-004` model.
  - Initialized both FastAPI and Vitest test suites to prevent contract regression during subsequent phases.

---

## Phase 1: Resume Core
- **Status**: Pending
- **What will be built**:
  - PDF parser utilizing PyMuPDF (with OCR fallback for scanned sheets).
  - LLM-driven structured extraction mapping resume text to a clean JSON profile database.
  - GitHub enrichment parser linking public repos, stars, and language breakdowns.
  - Tailored resume render engine compiling JSON profiles into Professional PDF (via WeasyPrint) and Word (`.docx` via python-docx) templates.
