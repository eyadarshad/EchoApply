# Kickoff & Per-Phase Prompts for Antigravity

## How to deploy (do this once)

1. Put the implementation plan in the repo at `docs/IMPLEMENTATION-PLAN.md` and create an empty `docs/PROGRESS.md`.
2. Copy `00-constitution.md` and `10-edge-cases.md` into `.agents/rules/` in your workspace. Set both to **Always On** (constitution) / **Always On or Model-Decision** (edge-cases) in the Customizations → Rules panel.
3. In the Agent Manager, select your workspace, set the model to **Gemini 3.5 Flash (high thinking)**, and start in **Planning mode**.
4. Paste the **Kickoff prompt** below. Approve the plan it produces. Then drive each phase with the **Per-phase prompt**.

---

## KICKOFF PROMPT (paste into Planning mode, once)

```
Read @docs/IMPLEMENTATION-PLAN.md, @.agents/rules/00-constitution.md, and
@.agents/rules/10-edge-cases.md in full before responding.

Your job: build this project part by part, one phase at a time, each phase
fully working and proven before the next. Follow the constitution exactly.

First, do PLANNING ONLY — do not write app code yet:
1. Produce a phased task-list Artifact derived from the plan's roadmap, in this order:
   Phase 0 — Scaffold: repo structure (Next.js app + FastAPI app), .env + .gitignore
             (secrets first), Supabase schema as real migrations (all tables in the
             plan's data model, with pgvector), the typed HTTP API contract between
             frontend and backend, and a CI/test runner. No features yet.
   Phase 1 — Resume core: upload → PyMuPDF parse → LLM structured extraction →
             GitHub enrich → generate ONE tailored resume (PDF + .docx).
   Phase 2 — Tailoring pipeline + technique library: the full decomposed pipeline
             (JD analysis → technique select → gap analysis → rewrite → impact →
             truthfulness gate → render), structured-output + validation + retry on
             every call, model routing (Flash high default, Pro for impact + truthfulness).
   Phase 3 — Jobs: JSearch + Jooble + remote APIs, async fan-out with per-source
             semaphores + backoff + cache, normalize → dedupe → rank (rule-based) →
             50 cards → top-10/50/100 → applied-job memory.
   Phase 4 — Tier-1 apply: pre-fill + LLM-drafted answers + ask-the-user-when-unsure,
             human submits.
   Phase 5 — v2 matching (embeddings + pgvector), then Phase 6 — Tier-2 agentic apply
             (Skyvern/Browser Use), opt-in.
2. For EACH phase, list its concrete acceptance criteria (what "done + proven" means)
   and which edge cases from the rulebook it must handle + test.
3. Identify every external library/API the phase needs and note: "verify version and
   current docs before use."

Then STOP and wait for my approval of the task list. Do not start Phase 0 until I say go.
```

---

## PER-PHASE PROMPT (reuse for each phase, fill in the number)

```
We are doing Phase <N> only. Re-read @docs/PROGRESS.md, the constitution, and the
edge-case rulebook first.

Execute Phase <N> to its acceptance criteria. Constraints:
- Verify every library version and API against real docs before using it. Do not
  invent function names, signatures, or model IDs.
- Build only what this phase specifies — minimal change, no scope creep.
- Handle and TEST every edge case the rulebook lists for this phase.
- For any app-side LLM call: structured output + schema validation + retry.
- A task is done only when it runs, tests pass, and you show proof (test output or a
  browser/screenshot Artifact).
- Commit each working slice with a clear message.

When the phase is complete:
1. Run the full test suite and show the output.
2. Update @docs/PROGRESS.md (built / verified / pending / decisions).
3. Give me a short summary + the proof Artifact, then STOP for my review before Phase <N+1>.

If anything is ambiguous or involves a real trade-off, pause and ask me — do not guess.
```

---

## Useful Antigravity slash commands for this build
- **`/grill-me`** before a fuzzy phase — makes the agent ask clarifying questions before coding (great for Flash, which otherwise guesses).
- **`/goal`** for a fully-specified phase — runs to completion without stopping for intermediate input.
- **`/browser`** when it needs to read live docs or test a running app.
- Keep phases in separate agent runs; use **Worktree mode** if you parallelize, so agents don't collide on files.

## Why this shape (not one mega-prompt)
A single giant prompt is exactly what makes a fast model drop rules. Splitting into an
always-on constitution + an edge-case rulebook + small per-phase prompts keeps each
request focused, keeps the critical constraints persistent, and forces proof at every
boundary. The structure is the reliability.
