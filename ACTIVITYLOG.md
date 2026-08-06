# ACTIVITYLOG.md

A running, chronological log of work done on SmartReco — read this first in any new chat session to pick up where things left off, since context doesn't carry across separate chat windows.

**This file is continuity/history only.** It is not authoritative for anything:
- [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) remains the mandatory phase-by-phase task tracker and the place for full technical rationale per decision.
- [`docs/SmartReco_SRS.docx`](docs/SmartReco_SRS.docx) remains the ultimate source of truth for requirements.

If this file ever conflicts with either of those on *what to build*, they win. This file only records *what happened and when*.

---

## Current Status

- **Last updated:** 2026-08-06
- **Where things stand:** Phases 0–5 complete and merged, plus the interim UI redesign (Stitch design system) and Docker Compose hardening/hot-reload work (PR #9), plus four follow-up fixes to Phase 4's recommendations flow. **Phase 6 (Bonuses) complete** — all 5 tasks merged: LangGraph refactor, metadata filtering, LangSmith tracing, APScheduler daily digest job, and SMTP email delivery (with a dev-only MailHog container for local testing).
- **Next up:** Phase 7 — Polish + Submit, per `docs/BUILD_PLAN.md` (finalize README, download the CI workflow from the hackathon dashboard - already done in an earlier session - `requirements.txt`, fresh-clone sanity pass). You haven't yet submitted the hackathon dashboard entry form, which is why CI's critical checks pass but the result isn't recorded (a known, repeatedly-noted gap, not something code can fix).
- **Your LangSmith API key and MailHog/digest email settings are in your local `.env`** (gitignored, never committed): `LANGCHAIN_PROJECT=pr-downright-collard-46` (traces land there), `SMTP_HOST=mailhog`/`SMTP_PORT=1025`/`DIGEST_FROM_EMAIL=digest@smartreco.dev` (digest emails land in MailHog's web UI at `localhost:8025` when the stack is running).
- **Blocking on you:** the hackathon dashboard entry-submission form still isn't filled in — CI checks run and pass, but per the CI's own error, results aren't recorded until that form is submitted. Not urgent, but needed before final submission. Also: Phase 3's client-side JS (`tracker.js`) was carefully code-reviewed and its backend calls verified live, but never executed in an actual browser — worth a quick real-browser spot-check (DevTools Network tab, browse the catalog, confirm a batched POST to `/events`) when you get a chance.

---

## Standing Instructions From You

Not phase-specific — still in force, and should keep being followed unless you say otherwise.

- Full workflow (branching, testing bar, git conventions) is defined in `CLAUDE.md`; **standing authorization to merge PRs** once a phase's Definition of Done is met and CI checks pass, without asking per-merge — only pause if something is a genuine surprise.
- For ambiguous SRS decisions, make the pragmatic call yourself and record it (in the PR description and `BUILD_PLAN.md`) rather than blocking to ask — matches the precedent already set in `BUILD_PLAN.md`'s "Decision" callouts.
- `docs/BUILD_PLAN.md` is the mandatory execution path; `docs/SmartReco_SRS.docx` is the ultimate source of truth. Update `BUILD_PLAN.md`'s checklist immediately per task, and add any new work discovered mid-phase to it as it happens.
- Dockerize the app and add a Makefile with proper `make` commands — done ahead of the original Phase 1 scope, at your request.
- **Docker Compose (`make` commands) is the only supported way to run or manually test the project** — no parallel local `uv run uvicorn` path. This applies to Claude Code too.
- **Admin accounts are only created via `make create-admin`**, never through the public `/register` form (no role selector there, by design — avoids a privilege-escalation hole).
- Read and update this file (`ACTIVITYLOG.md`) at the start/end of sessions or major tasks — instruction added 2026-08-05, now also written into `CLAUDE.md`.

---

## Activity Log

### 2026-08-05 — GitHub & repo setup
- Installed and authenticated GitHub CLI (`gh`), connected as `athul-2003`.
- Initialized this local folder as a git repo and connected it to [athul-2003/SmartReco](https://github.com/athul-2003/SmartReco) (both were empty at the time).

### 2026-08-05 — Project bootstrap (docs, root commit)
- Read `docs/SmartReco_SRS.docx` (extracted via docx XML parsing, since it's binary) and built a full understanding of the project.
- Created `README.md`, `docs/BUILD_PLAN.md` (phased execution plan derived from the SRS), and `CLAUDE.md` (workflow rulebook: phase execution, testing bar, git/PR conventions, industry-standard practices).
- Pushed as the root commit on `main` (nothing to branch from yet at that point).

### 2026-08-05 — CI enabled (PR #1)
- Downloaded the official hackathon CI workflow from the dashboard URL, added `.gitignore` + `.env.example`, set `MESH_API_KEY` and `SUBMISSION_TOKEN` as GitHub repo secrets via `gh secret set`.
- CI confirmed working (Mesh key valid) even though code-related checks were still red at this point (expected — no app code existed yet).

### 2026-08-05 — SQLModel + AGENTS.md (PR #2)
- Adopted **SQLModel** as the ORM (per an SRS update) instead of raw SQLAlchemy.
- Added `AGENTS.md`: documents **Library Skills** (official, version-synced AI coding-agent skills bundled with FastAPI/SQLModel), installed via `uvx library-skills`, wired into `CLAUDE.md`.
- Strengthened `CLAUDE.md`'s BUILD_PLAN-authority language (checklist updated per-task, new work added to the plan as discovered).

### 2026-08-05 — Phase 0: Mesh Spike (PR #3)
- `uv`-managed project scaffolded. `scripts/mesh_spike.py` proved Mesh connectivity live: one embedding call, one chat completion, both against the real API.
- Confirmed real, working Mesh model identifiers empirically (`sentence-transformers/all-minilm-l6-v2`, `openai/chat-latest`) since Mesh's own docs listing wasn't reliable.

### 2026-08-05 — Phase 1: Foundation (PR #4)
- FastAPI + SQLModel/SQLite app: session-based auth (register/login/logout, `passlib[bcrypt]`), role enforcement (`require_login`/`require_admin`) gating `/admin`. 8 tests.
- **At your request, ahead of the original Phase 1 scope:** Dockerized the app (`Dockerfile`, `docker-compose.yml` running the app + Qdrant) and added a `Makefile`.
- Installed GNU Make on this dev machine (`winget install ezwinports.make`) so `make` commands work locally, not just in CI.
- Fixed a real `passlib`/`bcrypt` incompatibility (pinned `bcrypt<4.1`) and configured `ruff` to stop false-flagging FastAPI's `Depends()` pattern.
- Verified live: full `docker compose build && up`, register/login/logout/role-gating all confirmed working through the container.

### 2026-08-05 — Phase 2: Catalog + Dual-Write (PR #5)
- Admin product CRUD (`/admin/products`) and public catalog (`/catalog` browse/search/filter/detail), both dual-written to SQLite + Qdrant with transactional rollback on any Mesh/Qdrant failure (FR-2.5). `scripts/seed_catalog.py` (batched ~100/Mesh call, resumable).
- **Dataset detour:** the SRS's two named dataset sources both came back from the Kaggle API with unconfirmed/unspecified licenses — not safe for a public repo. With your explicit sign-off at each step (you chose "search for a cleanly-licensed alternative first"), found and used a **CC0-1.0 (public domain)** family of 5 Udemy category datasets instead — genuinely better than either original option (cleanly licensed *and* more category diversity). Combined 5,000 rows into `scripts/data/courses.csv`, committed to the repo.
- You provided a Kaggle API token (`KAGGLE_API_TOKEN`, `KGAT_...` format) for this — used once to fetch dataset metadata/files, not stored anywhere in the repo.
- Found and fixed a Qdrant client/server version mismatch (pinned both sides) and a Dockerfile issue causing dev-dependency reinstalls on every container start.
- 24 tests total. Verified live against real Mesh + Qdrant: 1,500/1,500 SQL↔Qdrant sync, resumability confirmed, and a real (non-mocked) admin create/delete verified through the running app.

### 2026-08-05 — Makefile rework + `make create-admin` (PRs #6, #7)
- Renamed Makefile targets to the Docker Compose-standard convention (`up`, `up-build`, `down`, `build`, `logs`, `ps`), per your request.
- **Made Docker Compose the sole supported way to run/test the project** — dropped the parallel local `uv run uvicorn` path. This surfaced and fixed a real bug: `make seed` was writing to a different SQLite file than the one the containerized app actually reads (host path vs. container bind mount) — fixed by running seed *inside* the container.
- Did a full manual walkthrough of everything built in Phases 0–2 against the live stack (auth, roles, catalog browse/search/filter/detail, admin CRUD) — all confirmed working, including real dual-write side effects (Qdrant `points_count` moving correctly on create/edit/delete).
- Added `scripts/create_admin.py` + `make create-admin`: the only way to get an admin account (interactive email/password/confirm, idempotent — creates new, promotes an existing regular user, or no-ops if already admin). Public `/register` intentionally has no role selector.
- Verified live: fresh creation, promotion, and no-op cases all confirmed to log in and reach `/admin/products` correctly.

### 2026-08-05 — This file added
- Created `ACTIVITYLOG.md` and wired the read/update instruction into `CLAUDE.md`, per your request, so context survives across separate chat windows.

### 2026-08-05 — New SRS re-analysis (no `main` changes needed)
- You uploaded an updated `docs/SmartReco_SRS.docx`. Re-read it and diffed against `README.md`/`docs/BUILD_PLAN.md`: the only real delta was the ORM (SQLAlchemy → SQLModel), which was **already** reflected everywhere (see the "SQLModel + AGENTS.md" entry above) — so this was a confirmation pass, not new work. Everything else in the new SRS matched what was already documented.

### 2026-08-05 — Stitch UI design system rollout (uncommitted, before Phase 3)
- You connected a Google Stitch MCP server (blocked by a confirmed, currently-open bug on Google's side — schema `$ref` resolution failure, corroborated by multiple public issue reports for other MCP clients too) — worked around it by you sharing exported screenshots directly instead.
- Analyzed the sample design + your own `docs/DESIGN.md` (color/type/spacing tokens), then planned and implemented a full restyle of every Phase 1–2 template (`base.html`, auth pages, catalog browse/detail, admin) using those tokens — via `EnterPlanMode`, plan approved before implementing.
- Solved two open design problems: (1) no product images in the dataset → deterministic tonal cover + monogram per product, generated from `category` (`app/services/ui.py`), no schema/seed change; (2) "My Recommendations" page can't be real before Phase 4's agent exists → added only the cold-start empty state now (`/recommendations`), flagged explicitly as scaffolding in `docs/BUILD_PLAN.md`, not a Phase 4 skip-ahead.
- Also decided (with your sign-off via `AskUserQuestion`): dropped a "Skill Level" filter from the sample (not in the SRS schema), kept the sample's "AI Suggestion" box as a static placeholder, deferred match-percentage badges to Phase 4 (Qdrant already returns a real similarity score, so that can be genuine later, not fabricated).
- Verified live end-to-end with Playwright screenshots against the real running Docker stack (not just template review) — all 5 key screens, real seeded catalog, real admin account.
- Full details and all decisions: `docs/BUILD_PLAN.md`'s "Interim — Design System & UI Pass" section.

### 2026-08-05 — UI follow-up: nav visibility, real pagination, sort (uncommitted)
- Per your feedback on the first UI pass: nav bar now hidden entirely until login (you chose the strictest of 3 options — zero header anywhere while anonymous, including catalog/detail browsing); added real pagination to `/catalog` (was silently capped at 24 products with no way to see more); added a working sort dropdown and real per-category counts in the filter sidebar.
- Re-verified live via Playwright against the rebuilt stack; full test suite + `ruff` still passing.
- Details/decisions: `docs/BUILD_PLAN.md`, same Interim section's "Follow-up UI polish" subsection.

### 2026-08-05 — Docker Compose hardening + hot reload (uncommitted)
- You asked for local hot reload (previously every code change needed a full `make up-build` rebuild — code wasn't bind-mounted, no `--reload`), and for the Compose setup to be cleaner/production-ready.
- Added `docker-compose.override.yml` (bind-mounts `app/`+`scripts/`, adds `--reload`) — auto-merged by Compose whenever `docker-compose.yml` is, so `make up`/`make up-build` get hot reload for free with no Makefile changes; committed as shared dev tooling, not gitignored as a personal file.
- Hardened `docker-compose.yml` itself: healthchecks on both services (confirmed Qdrant's `/readyz` live before wiring it in), `depends_on: condition: service_healthy` (previously only waited for container *start*, not readiness), `restart: unless-stopped`, explicit image tag. `Dockerfile` now runs as a non-root user and has its own `HEALTHCHECK`.
- Added `make prod-build`/`prod-up`/`prod-down` (`-f docker-compose.yml` only, explicitly excluding the dev override) as the path a real deploy/CI would use.
- Answered two direct questions from you: no "official Docker skill" exists for this project (Library Skills only covers FastAPI/SQLModel, both tiangolo packages — Docker doesn't publish one that way) — applied standard Compose conventions by hand instead. And: the `DATABASE_URL`/`QDRANT_URL` overrides in `docker-compose.yml`'s `environment:` block are intentional, not redundant with `.env` — `.env` covers host-run `uv` commands, Compose's override covers the in-network reality (`localhost` means something different inside the app container than on the host) — now documented in both places so it doesn't look like an oversight again.
- Verified live: rebuilt, confirmed both services report healthy, confirmed hot reload actually reflects a template edit without a rebuild, confirmed `make prod-up` runs the same image with no bind mounts/no reload.

### 2026-08-05 — Activity log gap acknowledged
- This file hadn't been updated since it was created, despite the standing instruction to keep it current — the SQLModel re-analysis, the full Stitch UI rollout, the nav/pagination follow-up, and the Docker hardening above all happened without an entry until now. Caught up in this session; going forward, updating this file is part of finishing each piece of work, not a separate step to remember later.

### 2026-08-05 — Interim work merged (PR #9), Phase 3 starting
- A separate chat session picked this repo back up, found the interim UI + Docker work above still uncommitted, and merged it to `main` as PR #9 ("Interim: Stitch design system UI pass + Docker Compose hardening/hot-reload"). `Current Status` above updated to match — this file's own log entries had gone stale relative to git state (said "uncommitted" after it was actually merged), a small illustration of exactly why this file needs to be kept current, not just written once.
- Starting Phase 3 (Behavioral Tracking) on top of this new baseline.

### 2026-08-05 — Phase 3: Behavioral Tracking
- `events` table, `POST /events` (Pydantic-validated batch, 1–50 events, plain 401 not a page-redirect since it's a JS-only endpoint), and `static/js/tracker.js` (view/search/click/dwell, batches on 10s/20-events/page-unload, `fetch(keepalive)` with a `sendBeacon` fallback on unload). Wired into the (redesigned, per PR #9) catalog/detail templates via `data-*` attributes.
- **Found and fixed a real, severe Docker bug from PR #9's non-root-user hardening**, unrelated to tracking but blocking everything: `appuser` couldn't write to the bind-mounted `./data` directory (host-side ownership doesn't match the container user once the bind mount replaces the build-time-`chown`'d path) — broke `make up-build` for anyone. Fixed with the standard root-entrypoint-then-`gosu`-drop-to-appuser pattern (`docker-entrypoint.sh`). Added `.gitattributes` alongside it so the new shell script's LF line endings survive a Windows checkout.
- 37/37 tests passing. Verified live: a real event batch (matching the tracker's exact shape) correctly landed in `events` with the right user/type/product/metadata; confirmed the script/data-attributes render correctly (present only when logged in). Honest gap: the client-side JS logic itself was code-reviewed, not executed in a real browser — no browser/JS-runtime tool available in this environment to do that directly.

### 2026-08-05 — Phase 4: Agent Core (RAG Pipeline)
- `recommendations` table, `vector_store.search()` (top-K Qdrant retrieval, deferred from Phase 2), and `agent/nodes.py` — a straight function chain (`build_profile` → `retrieve_candidates` → `generate_narrative`) on purpose, not a graph: FR-4.5's LangGraph refactor is explicitly a later, additive Phase 6 step, so building a graph now would just be extra work for Phase 6 to undo.
- Extended `routers/recommendations.py` (the route already existed as a Phase-4-scaffolded cold-start-only empty state, from PR #9's interim UI pass) — `GET` now shows the latest stored recommendation, `POST /refresh` runs the real pipeline. `GET` never calls Mesh/Qdrant, only `/refresh` does — ahead of Phase 5's formal trigger/cache layer, but there was no reason for a page view to cost an LLM call regardless.
- 47/47 tests passing. **Verified fully live, no mocks:** simulated real Python/Development-focused browsing behavior (views, clicks, dwell, a search for "python for data science") for a test user, hit refresh (~6s — real Mesh embed + real Qdrant top-K + real Mesh chat generation), and got back a narrative that correctly referenced the actual behavioral signals, recommending 5 genuinely relevant courses — **all 5 confirmed to exist as real `products` rows**, zero hallucination. Confirmed `GET` is fast (93ms vs. refresh's 6.2s — no LLM call). Confirmed a zero-event user still correctly gets the cold-start empty state. Full clean `docker compose build` also verified, not just hot-reloaded.

### 2026-08-05 — Phase 4 follow-up: cold-start empty state had no way to trigger a first recommendation
- **You caught this one yourself**, testing in your own browser after Phase 4 merged: browsed the catalog (real events confirmed in the backend log), visited `/recommendations` repeatedly, and never saw anything but the empty state. The backend log you shared made the bug obvious — no `POST /recommendations/refresh` anywhere in the trace, because there was genuinely no button to trigger it. The refresh button only existed on the *already-has-a-recommendation* view; the empty state only ever linked back to `/catalog`.
- Root cause of why my own Phase 4 verification didn't catch this: I drove `POST /refresh` directly via `curl` to test the pipeline, never by clicking through the actual empty-state UI a real user would use — verified the backend thoroughly, missed a frontend gap.
- Fixed: `view_recommendations` now checks if the user has any tracked `Event`; if so, the empty state shows a primary "Generate My Recommendations" button. If not (true zero-activity), it keeps the original browse-first copy - no point offering to generate from nothing. Added a regression test and reverified live, reproducing your exact scenario end to end - confirmed working.

### 2026-08-05 — Phase 4 follow-up #2: auto-generate instead of a button
- Your feedback on the fix above: no separate "Generate" button/click needed at all - the first visit to `/recommendations` with real behavioral data should just show a recommendation automatically.
- Changed `GET /recommendations` to generate and store the first recommendation inline, the first time a user with tracked activity visits (no button anymore); `empty.html` reverted to its simple original form since it's now only reached by genuinely zero-activity users. This narrows (doesn't reverse) the "GET never calls Mesh" decision from Phase 4 proper - it still holds once a recommendation exists, just not for the one-time transition into having one.
- Updated tests (auto-generate replaces the button-presence test) and reverified live: a single visit after browsing now produces a real grounded recommendation directly (~6.8s, matching real generation cost), the next visit is fast (268ms, confirming no regeneration), and zero-activity users are unaffected. 48/48 tests passing.

### 2026-08-06 — Phase 4 follow-up #3: stream the narrative instead of blocking on it
- Your feedback on fix #2: the first visit still felt slow - a blank tab for ~6-7s with zero feedback. You asked specifically about streaming as an option.
- Split the pipeline: `prepare_candidates()` (fast - one Mesh embed + Qdrant top-K) now runs separately from narrative generation. `GET /recommendations` on a first visit runs retrieval only and renders real product cards immediately, with a pulsing "Thinking about what fits you best…" placeholder. A new `GET /recommendations/stream` (Server-Sent Events) streams the narrative in via `LLMClient.chat_stream()` (`stream=True`) for the exact candidates already shown - critically, it does **not** re-embed or re-query Qdrant, avoiding a duplicate Mesh cost. `app/static/js/recommendations-stream.js` (`EventSource`, same pattern as `tracker.js`) appends chunks as they arrive.
- Deliberately scoped to the first-generation path only - `POST /refresh` keeps its simple synchronous pattern, since that's used when the user already has content on screen and a clear "I clicked something" expectation, unlike the blank-tab first visit.
- Reverified live: retrieval-only render dropped to ~2-3s (after container warm-up) vs. the full ~6-7s before; the narrative streamed as 5 distinct real SSE chunks (confirmed via raw `curl -N`), completing in well under a second once retrieval had finished; full narrative + correct `product_ids` persisted correctly; a follow-up visit still serves the stored recommendation via the normal fast path. 51/51 tests passing.

### 2026-08-06 — Phase 4 follow-up #4: streaming crash (`IndexError`), from a real traceback you pasted
- You tried the streaming feature and it still hung, and this time you pasted the actual container traceback: `IndexError: list index out of range` at `chunk.choices[0]` in `chat_stream()`. Real bug, not a UX issue - Mesh's streaming API sends at least one chunk with an empty `choices` list (common OpenAI-compatible pattern, e.g. a trailing usage/metadata chunk), which crashed the whole SSE generator the moment it arrived - narrative never finished, nothing got persisted, you were stuck on the placeholder forever.
- Fixed the root cause (`chat_stream()` now skips empty-`choices` chunks) and added defense-in-depth in the router: the SSE loop is now wrapped so any failure degrades gracefully - partial content already streamed gets persisted anyway (better than losing it), and a clean `event: failed` (not `event: error`, which collides with `EventSource`'s built-in connection-error handling) tells the client to show a retry message if nothing streamed at all.
- Added a direct regression test reproducing the exact empty-choices scenario, plus two SSE-endpoint failure-path tests. Reverified live: the exact request that crashed before now completes in well under a second, repeated 3x back-to-back with zero errors in the logs, correct persistence every time. 54/54 tests passing.

### 2026-08-06 — Phase 5: Triggers + Caching
- `agent/triggers.py::should_auto_regenerate()` — counts a user's `events` rows created after their latest `Recommendation`; auto-regenerates once **5** have accumulated since. `GET /recommendations` now branches three ways: no recommendation + no activity → empty state; no recommendation + activity → first-generation (unchanged from Phase 4, `trigger_reason="manual"`); recommendation exists but the threshold has been crossed → same streaming `generating.html`/`/stream` flow reused from Phase 4, `trigger_reason="threshold"`. Below the threshold, the cached row is served directly with no Mesh/Qdrant call at all.
- Reused rather than duplicated Phase 4's streaming UX for the auto-regenerate case — extracted `_render_generating()` so both the first-visit and threshold-crossing paths share it. The `trigger_reason` had to survive two separate HTTP requests (the page GET that decides to regenerate, then the browser's own `EventSource` GET to `/stream` that actually persists the result) — threaded through as a `reason` query param, rendered into a `data-trigger-reason` attribute by `generating.html`, read and appended to the SSE URL by `recommendations-stream.js`.
- `POST /refresh` (manual button) is unaffected — always regenerates immediately regardless of event count, keeps storing `trigger_reason="manual"`, per the SRS's manual-refresh guarantee.
- New `tests/test_triggers.py` (threshold math in isolation) plus new router-level tests in `tests/test_recommendations.py` (cache-hit asserts `prepare_candidates` is never called below threshold; auto-regenerate fires at exactly 5 events with the right `trigger_reason`; `/stream`'s `reason` param persists correctly). 62/62 tests passing, `ruff` clean.
- **Verified live against the real running stack, no mocks:** registered a fresh user, 2 real events → first `GET` correctly streamed and persisted a real Mesh narrative (`trigger_reason="manual"`); immediate re-view served the cache in 158ms; sent 5 more real events to cross the threshold → next `GET` correctly auto-regenerated (`trigger_reason="threshold"`, ~2.1s retrieval-only) with a genuinely different narrative; the view after that dropped back to the ~140ms cached path. Confirmed both rows landed in the container's real SQLite DB with the correct `trigger_reason` values, in order, via `docker compose exec app uv run --no-sync python -c ...`.

### 2026-08-06 — Phase 6 (Bonus): LangGraph refactor of the manual-refresh pipeline
- You asked whether SMTP was really the best choice for the later email-digest bonus, vs. AWS SES or a local test catcher like MailHog. Recommended sticking with plain SMTP (matches the SRS decision already in `BUILD_PLAN.md`, zero new cloud dependency) but adding a MailHog container for local dev testing so the real "sent" path can be demonstrated without your real credentials; you agreed via `AskUserQuestion`. That work lands later in this same phase.
- `app/agent/graph.py` — new `langgraph.graph.StateGraph` (analyze → retrieve → evaluate → refine-if-weak → generate), reusing `build_profile`/`retrieve_candidates`/`generate_narrative` from `agent/nodes.py` as node bodies. A weak top Qdrant match (cosine score < 0.35) triggers exactly one wider retrieval attempt (3x `top_k`) before generating; a permanently-weak result still terminates rather than looping.
- Scoped to `POST /refresh` only, on purpose - `GET /recommendations`'s first-generation/auto-threshold paths keep the Phase 4/5 streaming split (`prepare_candidates` + `generate_narrative_stream`), since a single blocking `graph.invoke()` would undo that UX. Removed the now-superseded `nodes.generate_recommendation()` rather than leaving it as dead code; the router's import swapped to `run_recommendation_graph` aliased to the same name, so the router body itself didn't need to change.
- New `tests/test_graph.py` (happy path, empty-candidates fallback, weak-score refine-once, max-attempts termination); 64/64 tests passing, `ruff` clean.
- Verified live against the rebuilt real stack (fresh image needed - `langgraph` is a new dependency): real Business-category browsing events → `POST /refresh` (~9.4s, real Mesh+Qdrant+Mesh through the graph) produced a narrative genuinely grounded in that behavior, all 5 recommended product IDs confirmed as real rows in the container's DB, no errors in logs.

### 2026-08-06 — Phase 6 (Bonus): metadata filtering
- `vector_store._build_filter()` builds a Qdrant `Filter` from optional `category`/`max_price` args against payload fields already on every point; threaded through `retrieve_candidates` → the LangGraph's `_retrieve` node (both the initial and refined attempts respect it) → `run_recommendation_graph`, and exposed as optional `category`/`max_price` query params on `POST /refresh` so it's a real callable feature, not just internal plumbing.
- New `tests/test_vector_store.py` plus pass-through tests across the call chain; 73/73 tests passing, `ruff` clean.
- Verified live against the real 1,500-product Qdrant collection: `category=Business` narrowed 1500→300, adding `price<=2000` narrowed further to 74; called the real `POST /refresh?category=Business&max_price=2000` endpoint and confirmed every one of the 15 returned recommendations was genuinely Business + ≤₹2000 by querying the container's actual SQLite DB. Noticed the narrower filtered corpus pushed the top match's score below the LangGraph refine threshold from the previous sub-task, which correctly triggered a widened retry - the two Phase 6 features compose correctly together.

### 2026-08-06 — Phase 6 (Bonus): LangSmith tracing, plus a real test-isolation bug it surfaced
- `app/observability.py::configure_langsmith()` propagates `LANGCHAIN_TRACING_V2`/`LANGCHAIN_API_KEY`/a new `LANGCHAIN_PROJECT` setting into `os.environ` at startup (pydantic-settings parses `.env` into our own object, doesn't touch `os.environ`, which is what LangSmith's own auto-instrumentation actually reads) - no explicit tracer wiring needed in `agent/graph.py`, matches the SRS's "instrumentation-only" framing.
- **You caught a real gap in my first pass**: I only set the `LANGCHAIN_*` env var names (matching the SRS's literal wording), but your LangSmith dashboard's own quickstart snippet showed `LANGSMITH_PROJECT` instead. Checked the installed SDK's actual source rather than guessing - confirmed `LANGSMITH_*` genuinely takes precedence over `LANGCHAIN_*` in the version installed here. Fixed to set both, added a `langchain_project` setting (default `"smartreco"`), and set it in your local `.env` to your dashboard's actual project name (`pr-downright-collard-46`) so live traces land where you can see them.
- You provided a real LangSmith API key for live verification. Set it in `.env` (gitignored). While testing, **found and fixed a real bug this surfaced**: `app.main` calls `configure_langsmith()` at import time, and every test imports `app.main` via `conftest.py` - with real tracing enabled locally, running `uv run pytest` was silently sending every automated test's LangGraph invocations as real traces to LangSmith (confirmed via the API: 4 traces clustered within ~1.3s, matching `test_graph.py`'s 4 graph-invoking tests). This is exactly the "never hit real external services in automated tests" rule that already applied to Mesh/Qdrant/SMTP, just not previously extended to LangSmith. Fixed with an `autouse` fixture in `tests/conftest.py` that clears the tracing env vars before every test.
- 77/77 tests passing (new `tests/test_observability.py`), `ruff` clean. **Live-verified against the real LangSmith API** (not just visual dashboard trust): ran a real `POST /refresh`, then queried `/sessions` + `/runs/query` directly - confirmed a root `LangGraph` run (`status: success`) landed in your named project, with the full `analyze → retrieve → _evaluate_retrieval → generate` node structure nested correctly underneath. Re-ran the test suite afterward and confirmed via the API that zero new traces landed - the fix holds.

### 2026-08-06 — Phase 6 (Bonus): APScheduler daily digest + SMTP email delivery — Phase 6 complete
- `services/email.py::send_email()` (plain `smtplib`, logs the rendered email instead of sending if `SMTP_HOST` is unset) + `services/digest.py::run_daily_digest()` (runs the same LangGraph pipeline the manual refresh button uses, for every user with at least one tracked event; skips - doesn't email - users with no grounded candidates) + `scheduler.py` (`APScheduler` `BackgroundScheduler`, one daily cron job, started/stopped from `main.py`'s lifespan).
- Deliberately does **not** persist a `Recommendation` row for the digest - it's a side-channel email nudge, not a state change to what the user sees on their next `/recommendations` visit; doing so would silently interact with Phase 5's caching logic for something nobody asked for.
- Added a `mailhog` service to `docker-compose.override.yml` (dev-only, excluded from `make prod-*`) so the real "sent" SMTP path could be demonstrated without real credentials - `SMTP_HOST=mailhog`/`SMTP_PORT=1025` in `.env` routes there, viewable at `localhost:8025`.
- 87/87 tests passing (new `test_email.py`, `test_digest.py`, `test_scheduler.py`), `ruff` clean. **Live, against the real stack with a real MailHog container, no mocks:** registered two fresh users with real tracked events, ran the digest job directly inside the container against the real DB/Mesh/Qdrant - sent 20 real emails (every active user from this session's testing). Queried MailHog's own REST API directly and confirmed all 20 landed with correct `To`/`Subject`; inspected one full body and confirmed a real, coherent, behaviorally-grounded digest with genuine product titles/prices - same pipeline, same quality bar as the manual refresh button.
- **This closes out Phase 6** - all 5 bonus tasks (LangGraph, metadata filtering, LangSmith tracing, APScheduler, email delivery) now merged to `main`.
