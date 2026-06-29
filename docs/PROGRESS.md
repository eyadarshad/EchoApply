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

---

## Phase 4: Smart Apply (Tier 1)
- **Status**: Completed & Verified
- **Date**: 2026-06-29
- **What was built**:
  - `/apply/draft` endpoint that drafts personalized, truth-abiding answers to screening questions using Gemini (FastAPI skill experience, visa sponsorship, expected salary, notice period) and calculates confidence scores/warnings.
  - `/apply/submit` endpoint with duplicate-application checks and database-less fallbacks.
  - Glassmorphic slide-out `ApplyDrawer.tsx` component displaying questions with `Auto-Filled` and `Needs Input` status badges.
  - Submitting applications records state, shows a circular check success feedback block, closes, and updates job cards to display the green check `Applied` badge and a `Re-apply` button action.
- **Verification**:
  - Created unit/integration tests in `backend/tests/test_apply.py` verifying draft logic, submission success, and duplicate handling.
  - Ran the full test suite (`pytest`) verifying all 30 tests pass.
  - Walked through E2E apply flow in the browser and captured:
    - [apply_drawer_prefill.png](file:///C:/Users/EYAD/.gemini/antigravity-ide/brain/7e7162d5-5854-4d32-83be-896086a1e4d4/apply_drawer_prefill.png)
    - [apply_success.png](file:///C:/Users/EYAD/.gemini/antigravity-ide/brain/7e7162d5-5854-4d32-83be-896086a1e4d4/apply_success.png)
    - [applied_badge.png](file:///C:/Users/EYAD/.gemini/antigravity-ide/brain/7e7162d5-5854-4d32-83be-896086a1e4d4/applied_badge.png)
- **Decisions**:
  - Created a robust type check for unpacking the `IN_MEMORY_JOB_CACHE` tuple, supporting both tuple and dictionary cache fallback schemas.
  - Added warning descriptions in the UI when confidence was below `0.5`, explaining exactly why the field was not auto-filled (e.g. salary expectations not specified on the resume).

---

## Phase 5: Semantic Match Scoring & Explainability
- **Status**: Completed & Verified
- **Date**: 2026-06-29
- **What was built**:
  - Implemented 768-dimensional Job Description and Resume Profile embedding generation using the Gemini API.
  - Developed a blended hybrid matching engine (50% semantic similarity + 50% keyword-based scoring) with clean, robust normalization scaling.
  - Implemented concurrent Gemini-powered match explanations for the top 3 job results.
  - Updated the frontend to call `POST /profiles` upon manual setup edits to persist profiles and trigger embedding generation in the database.
  - Provided graceful fallback logic for database-offline and rate-limiting (429) conditions.
  - **Loud Warnings & UI Degradation Flags**: Added mechanism to log loud errors and flag matching explanations with degraded match warnings if deterministic dummy vector fallbacks are triggered.
  - **Transparent Formula Breakdowns**: Surfaced detailed math formula breakdowns `[Semantic Match: X% | Keyword Match: Y% | Blend: 0.5*X% + 0.5*Y% = Z%]` directly in the matching explanations.
- **Verification**:
  - Authored a comprehensive unit/integration test suite in `backend/tests/test_matching_v2.py`.
  - Ran the full test suite (`pytest`) verifying all 36 tests (34 passed, 2 skipped due to offline db pgvector queries) pass successfully with 0 regressions.
  - Verified and captured a browser screenshot displaying transparent blend scores, custom Gemini rationales, and fallback degradation warnings:
    - [semantic_matching_results.png](file:///C:/Users/EYAD/.gemini/antigravity-ide/brain/7e7162d5-5854-4d32-83be-896086a1e4d4/semantic_matching_results.png)
- **Decisions**:
  - Decided to perform embedding calculations on the normalized serializations of resume profiles and job listings.
  - Utilized concurrent `asyncio.gather` requests for fetching match explanations, optimizing search response times significantly.
  - Added robust validation fallbacks in uvicorn and pytest to serve heuristic descriptions if Gemini API calls fail or return 429 quota exceptions.
  - Reset and tracked `llm_client.fallback_occurred` within each search execution context to dynamically toggle warning flags in matching explanations.

---

## Phase 6: Tier-2 Agentic Auto-Apply
- **Status**: Completed & Verified
- **Date**: 2026-06-29
- **What was built**:
  - Opt-in browser automation agent `run_auto_apply_agent` in `backend/app/services/browser_agent.py` using Playwright.
  - Case-insensitive label-to-element mapping for standard fields (names, email, phone, github, linkedin) and custom screening answers.
  - Automated detection of CAPTCHAs, login redirects, and unmapped required fields, halting and triggering a graceful handoff to the candidate.
  - Sandbox test endpoints `/mock-apply-form` and `/mock-apply-submit` in `backend/app/main.py`.
  - Frontend checkbox toggle and interactive handoff screens in `frontend/src/components/ApplyDrawer.tsx`.
- **Verification**:
  - Created automated unit tests in `backend/tests/test_auto_apply_agent.py` running against the sandbox mock server, verifying successful apply, login blocking, CAPTCHA blocking, and unmapped required fields blocking.
  - Full backend test suite executed and passed (38 passed, 2 skipped due to offline db).
- **Decisions**:
  - Standardized submitting custom screening answers using their full question texts as dictionary keys to enable precise substring matching against web page labels.
  - Standardized screenshots of form states (`auto_apply_filled.png`, `auto_apply_blocked.png`) saved to both workspace and artifacts directory.
