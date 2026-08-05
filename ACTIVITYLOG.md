# ACTIVITYLOG.md

A running, chronological log of work done on SmartReco — read this first in any new chat session to pick up where things left off, since context doesn't carry across separate chat windows.

**This file is continuity/history only.** It is not authoritative for anything:
- [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) remains the mandatory phase-by-phase task tracker and the place for full technical rationale per decision.
- [`docs/SmartReco_SRS.docx`](docs/SmartReco_SRS.docx) remains the ultimate source of truth for requirements.

If this file ever conflicts with either of those on *what to build*, they win. This file only records *what happened and when*.

---

## Current Status

- **Last updated:** 2026-08-05
- **Where things stand:** Phases 0–3 complete and merged to `main` (7 PRs), plus the interim UI redesign (Stitch design system) and Docker Compose hardening/hot-reload work (PR #9). Phase 3 (Behavioral Tracking) just landed — event model, tracker.js, ingestion endpoint, wired into the catalog/detail templates.
- **Next up:** Phase 4 — Agent Core (RAG Pipeline), per `docs/BUILD_PLAN.md`.
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
