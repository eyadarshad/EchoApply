# AI Resume Generator & Smart Apply — Implementation Plan

*Final build plan. Version 1.0.*

---

## 1. What we're building

A system that takes a user's existing resume + GitHub / LinkedIn / portfolio, understands them deeply, then for **each target job** produces a **single tailored resume** that simultaneously:

- **Passes the ATS** (parseable, keyword-matched to the job description), and
- **Stops a human's scroll** (typographic hierarchy, whitespace, a tailored anchor line, quantified achievements).

It then finds relevant jobs/internships, ranks them, remembers what's already been applied to, and assists with applying — pre-filling forms and drafting screening answers, with the user in the loop on submit.

### The three layers (build in this order of value and safety)

| Layer | What it does | Difficulty | Risk |
|---|---|---|---|
| **A. Resume engine** | Parse → enrich → tailor → render one resume per job | Easy | Low / legal |
| **B. Job aggregation + matching** | Pull jobs via APIs, rank, dedupe, remember applied | Medium | Low if API-based |
| **C. Apply** | Pre-fill + draft answers (semi-auto), then optional agentic auto-apply | Hard | High on big sites |

Layer A alone is already a usable product. Don't wait for C to ship A.

---

## 2. Guiding principles

1. **Legal, valuable core first.** The resume engine and API-based job search are fully legitimate and high-value. Full auto-apply on LinkedIn/Indeed/Glassdoor violates their ToS and risks banning the user's real account — so it's an *opt-in frontier*, not the foundation.
2. **Truthful tailoring only.** We optimize for ATS the legitimate way (clean parsing + real keyword matching). We **do not** build hidden-text keyword stuffing or prompt-injection against AI screeners — those are detectable, get candidates blacklisted, and backfire. Every rewrite rephrases and surfaces *real* experience; it never fabricates.
3. **One resume, both requirements.** ATS-parseable and human-scannable don't conflict. A clean single-column doc with strong hierarchy satisfies both. No separate "modes."
4. **Build smart, not from scratch.** Use free APIs and prebuilt agent frameworks (Skyvern / Browser Use) instead of hand-writing parsers and per-site bots.
5. **Decompose every LLM task.** Small focused calls beat one mega-prompt. The model is never the bottleneck — orchestration is.
6. **Human-in-the-loop on submit.** The bot does 95%; the user confirms the final send. Faster to build, more reliable, and protects accounts.

---

## 3. Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────────┐
│  Next.js (App Router)        │  HTTP   │  FastAPI (Python)                │
│  — UI, auth, streaming       │ ──────► │  — parsing, embeddings           │
│  — caching of job results    │ ◄────── │  — LLM orchestration / pipeline  │
│  — Server Actions            │         │  — job aggregation (async)       │
│  Deployed: Vercel            │         │  — resume render (PDF/docx)      │
└─────────────────────────────┘         │  — browser agents (apply)        │
                                         │  Deployed: Render / Railway      │
                                         └──────────────┬───────────────────┘
                                                        │
                          ┌─────────────────────────────┼─────────────────────────┐
                          ▼                              ▼                         ▼
                  ┌───────────────┐          ┌────────────────────┐    ┌──────────────────┐
                  │ Supabase      │          │ LLM router          │    │ External APIs    │
                  │ Postgres +    │          │ Gemini / Groq /     │    │ JSearch, Jooble, │
                  │ pgvector +    │          │ OpenRouter          │    │ GitHub, remote   │
                  │ auth + storage│          │ (OpenAI-compatible) │    │ job boards       │
                  └───────────────┘          └────────────────────┘    └──────────────────┘
```

**Why the hybrid (Next.js + FastAPI) and not one stack:** the heavy lifting — resume parsing, embeddings, and the browser agents — is strongest in Python and can't run inside Next.js. Next.js gives us streaming Server Components (resume/answers stream into the UI live), Server Actions, built-in caching for scarce job-API quotas, and SSR/SEO if this becomes a multi-user product. Cost of the hybrid: two deployments + one API contract to keep in sync. Worth it for the capability.

---

## 4. Tech stack & rationale

| Concern | Choice | Why this over alternatives |
|---|---|---|
| Frontend | **Next.js (App Router) + TS + Tailwind** | Streaming, caching, SSR. Vite SPA loses the server layer; full-Next monolith can't run Python agents. |
| Backend | **FastAPI (Python)** | Async-native (concurrent API/LLM calls), Pydantic for structured-output validation. Django is sync/page-oriented; Node splits you from Python ML libs. |
| DB | **Supabase (Postgres + pgvector + auth + storage)** | One service for DB, vectors, auth, files. Avoids a separate vector DB (Pinecone/Chroma). |
| LLM access | **OpenAI-compatible router across Gemini / Groq / OpenRouter** | Free tiers with independent quotas → stack them. Swap models by string. |
| Resume parsing | **PyMuPDF (text) → LLM structured output** | Free-tier friendly, schema you control. Parser APIs (Affinda/LoopCV) kept as fallback. |
| GitHub enrichment | **GitHub REST API** | Official, free, generous. No scraping. |
| LinkedIn enrichment | **User uploads LinkedIn "Save to PDF" export** | Fully legal; reuses the parser. No scraping (ToS/ban risk). Proxycurl only if budget later. |
| Portfolio/any URL | **Jina Reader (`r.jina.ai`)** | Free clean-markdown extraction. Firecrawl if JS-heavy. |
| Render | **HTML+CSS → PDF (WeasyPrint)** + **.docx (python-docx)** | Best ATS parsing + control. .docx often parses most reliably in ATS. |
| Job aggregation | **JSearch (primary) + Jooble + remote APIs** | See §8. |
| Matching | **Rule-based v1 → embeddings + pgvector v2** | Ship fast, add semantic later. |
| Applied-job memory | **Postgres unique constraint on `job_hash`** | Cannot double-apply. No vector magic needed. |
| Apply (Tier 2) | **Skyvern or Browser Use** | Prebuilt agentic form-fillers; vision/DOM-driven, resilient to layout changes. |
| Concurrency | **asyncio + per-source semaphores + tenacity backoff + cache** | Parallel without 429-ing tiny free quotas. |

---

## 5. Data model (core tables)

```
users            (id, email, major/domain, location, created_at)
profiles         (user_id, parsed_resume_json, github_json, linkedin_json,
                  portfolio_json, profile_embedding vector)
jobs             (id, source, title, company, location, remote, jd_text,
                  apply_url, jd_embedding vector, fetched_at, job_hash)
applications     (user_id, job_id, job_hash, status, applied_at,
                  UNIQUE(user_id, job_hash))   ← the dedupe guarantee
tailored_resumes (id, user_id, job_id, content_json, pdf_path, docx_path,
                  ats_score, created_at)
technique_library(id, technique, applies_to_major[], reader_weight,  ← ATS vs human
                  source_url, last_verified)
job_cache        (query_hash, results_json, expires_at)
```

`job_hash = sha256(normalize(title + company + location))` — used both for dedupe and cache.

---

## 6. The resume tailoring pipeline (the heart of the system)

**Output contract:** for every job, exactly **one** resume that satisfies **both** ATS-parseable and human scroll-stop. Always. No modes.

Decomposed into small, focused LLM calls. Each stage validated with Pydantic + auto-retry on schema failure.

| # | Stage | What it does | Model | Thinking |
|---|---|---|---|---|
| 1 | **JD analysis** | Extract hard reqs, nice-to-haves, exact skill phrasings, seniority → JSON | 3.5 Flash | low |
| 2 | **Technique selection** | Pull the technique subset for the user's major from `technique_library` | (no LLM — DB query) | — |
| 3 | **Gap analysis** | Match JD reqs vs user's *real* experience → hit / partial / missing | 3.5 Flash | medium |
| 4 | **Targeted rewrite** | Rephrase real bullets to mirror JD language; reorder for relevance | 3.5 Flash | high |
| 5 | **Impact pass** | Write the anchor line, quantify + front-load top bullets, build highlights strip | 3.5 Flash (high) → **3.1 Pro if weak** | high |
| 6 | **Truthfulness check** | Flag any rewritten bullet that drifts from source resume; user confirms | **3.1 Pro** | high |
| 7 | **Render** | Structured content → ATS-safe single-column template → PDF + .docx | (no LLM — template code) | — |

**Key design rules:**
- **The model never renders the PDF.** Stages 1–6 produce *structured data*; Stage 7 is deterministic template code. This is why design quality doesn't depend on the model.
- **Truthfulness gate (Stage 6) is non-negotiable.** It's what keeps "aggressive keyword matching" from sliding into fabrication.
- **Route by difficulty.** Default everything to Gemini 3.5 Flash (it matches/beats 3.1 Pro on agentic tasks per Google's benchmarks, faster + cheaper). Escalate only the judgment-heavy steps (5, 6) to Pro. Keep both behind a router string for per-stage A/B. *(Model strings shift fast — verify current IDs; 3.5 Pro may be available now.)*

### "Stop the scroll" levers (all ATS-safe, baked into Stages 5 + 7)
- **Anchor line** under the name — one tailored value prop per job.
- **Front-loaded numbers** — top 2–3 bullets lead with a real metric (digits are visual anchors).
- **Golden-zone highlights strip** — key relevant skills in the first ~2 seconds of the F-pattern scan.
- **Hierarchy via type, not graphics** — bold name, clear section weights, one accent color.
- **Whitespace + density control** — generous margins, one page under ~10 yrs experience.

### Technique library (the "learn from internet, pick by major" part)
- Curated **once**, vetted, each technique tagged by `major` and `reader_weight` (ATS vs human).
- Selected per user at Stage 2 — *not* live-googled per request.
- An **offline refresh job** periodically re-evaluates sources and updates the library. That's the "learn from the internet" part — batch, not hot-path.

---

## 7. Layer A — Resume engine (Weeks 1–2)

1. **Intake:** upload PDF → PyMuPDF text → LLM structured extraction → `profiles.parsed_resume_json`.
2. **Enrichment (concurrent):**
   - GitHub REST API → repos, languages, READMEs, stars, activity.
   - LinkedIn → user uploads their own "Save to PDF" export → reuse parser.
   - Portfolio/URLs → Jina Reader → markdown → LLM summary.
3. **Tailoring pipeline** (§6) runs per selected job.
4. **Render:** ATS-safe single-column template → PDF (WeasyPrint) + .docx.

---

## 8. Layer B — Job aggregation + matching, tuned for Pakistan (Weeks 2–3)

**Key insight:** don't integrate Rozee / Mustakbil directly (no public dev API; scraping is brittle + ToS-risky). Reach them *through aggregation*.

| Source | Role | Notes |
|---|---|---|
| **JSearch** (RapidAPI) | **Primary** | `country=pk`; pulls from Google for Jobs, which indexes LinkedIn PK, Indeed PK, Rozee, Mustakbil. Free ~200 calls/mo → **cache hard**. |
| **Jooble** | Secondary | REST API, Pakistan presence. |
| **Remotive / RemoteOK / Arbeitnow / We Work Remotely** | Remote roles | Free. **Strategically important** — remote is where PK devs get best comp. Make it a first-class filter. |
| **Mustakbil (via JSearch/Google-for-Jobs)** | Gulf coverage | KSA/UAE/Qatar/Oman/Kuwait — relevant for Gulf-targeting users. |
| ~~Adzuna~~ | **Dropped for PK** | Pakistan not in its ~19-country coverage. Only useful for India/remote-intl targeting. |

**Flow:** concurrent fan-out → normalize to one schema → dedupe by `job_hash` → rank → 50 cards → top-10/50/100 slice.

**Matching:**
- v1 (ship first): rule-based score = keyword overlap + title match + location/remote + recency.
- v2: embed profile + each JD, store in pgvector, rank by cosine similarity for semantic matches ("ML engineer" ≈ "applied scientist"). Use the LLM to *explain* the top matches, not to rank all 50.

**Applied-job memory:** check `applications` for `(user_id, job_hash)` before applying; insert after. The unique constraint makes double-applying impossible.

---

## 9. Layer C — Apply (Week 4+, tiered by risk)

**Tier 1 — Semi-auto (build first).** Per job: pre-fill the form with user data; LLM drafts every screening answer from known info; flag anything uncertain for the user; user reviews and clicks submit on the real site. This *is* the "answer additional questions, ask when unsure" behavior — minus the ban risk.

**Tier 2 — Agentic auto-apply (opt-in, careful).** Use a prebuilt agent instead of per-site selectors:
- **Browser Use** (Python) — largest ecosystem, ~89% WebVoyager, fits the Python backend. Good default.
- **Skyvern** — vision + LLM, resilient to layout changes, self-hostable, explicitly built for form-filling and job applications. Strong pick for the apply step.
- Pattern: plain Playwright for the predictable 80%, AI agent for the 20% that needs understanding.
- Reality: agents hit ~70–85% on novel tasks, so keep a human-confirm step before final submit. Point Tier 2 **only** at accounts/sites the user accepts the risk on.

---

## 10. Concurrency & rate-limit strategy

Free tiers are tiny, so naive "fire everything at once" 429s instantly. The real design:
- `asyncio.gather` across sources, but a **per-source semaphore** capping concurrency to each source's limit.
- **Exponential backoff retry** (`tenacity`) on 429/5xx.
- **Cache layer** (Postgres `job_cache` or Redis) keyed by query, few-hours TTL — survives JSearch's ~200/mo quota and repeated searches.
- Same pattern for LLM calls: parallelize across jobs, rate-limit per provider, route across Gemini/Groq/OpenRouter to spread load over independent quotas.

---

## 11. LLM routing & free-tier reality

- **Default:** Gemini 3.5 Flash (high thinking) for the pipeline. **Escalate:** 3.1 Pro / 3.5 Pro for Stages 5–6 only.
- **Stack free tiers:** Gemini (~1,500 req/day) + Groq (fast, OpenAI-compatible) + OpenRouter (breadth + fallback) via one router.
- **Caveat:** free tiers usually train on your prompts and have no SLA. Fine for *your own* dev/use; the moment real users' sensitive data flows through, move the sensitive calls to a paid tier.
- ⚠️ "Grok" (xAI, paid) ≠ "Groq" (fast inference, free tier). Use **Groq**.

---

## 12. Build roadmap (vertical slices — working software each week)

1. **Week 1 — Resume core:** upload → parse → GitHub enrich → generate one tailored resume (PDF). *Already a usable product.*
2. **Week 2 — Tailoring pipeline + technique library:** full §6 pipeline with truthfulness gate; ATS-safe template.
3. **Week 3 — Jobs:** JSearch + Jooble + remote APIs → 50 normalized cards → rule-based ranking → top-10/50/100 → applied-job memory.
4. **Week 4 — Tier-1 apply:** pre-fill + LLM-drafted answers, human submits.
5. **Later — v2 matching (pgvector)** then **Tier-2 agentic apply** (Skyvern/Browser Use), opt-in.

---

## 13. Risks & guardrails

| Risk | Mitigation |
|---|---|
| **Account bans** from auto-applying on LinkedIn/Indeed/Glassdoor | Semi-auto (human submits) as default; Tier-2 only on accepted-risk accounts/sites. |
| **Fabrication** during rewrite | Truthfulness gate (Stage 6) + constrained prompts + user confirm. |
| **ATS black-hat tricks backfiring** | Not built. Legitimate optimization only. |
| **Free-quota exhaustion** | Aggressive caching + per-source rate limits + provider routing. |
| **Schema drift from LLM** | Structured output + Pydantic validation + auto-retry. |
| **Privacy** (users' data through free tiers that train) | Keep free tiers for dev/own use; paid tier for multi-user sensitive data. |
| **Scraper brittleness** (if Rozee scraper added later) | Prefer Google-for-Jobs aggregation; treat direct scraping as risky v2 opt-in. |

---

## 14. Out of scope for v1

- Direct Rozee/Mustakbil scraping (use aggregation instead).
- Full unattended auto-apply across all sites.
- A drag-and-drop resume editor (huge scope; the generator covers it).
- Proxycurl / paid LinkedIn enrichment (use the free PDF-export shortcut).

---

*Next concrete step: scaffold the repo (Next.js + FastAPI skeleton, the API contract between them, and the Week-1 resume slice wired end to end).*
