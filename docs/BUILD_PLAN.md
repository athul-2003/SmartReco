# SmartReco — Phased Build Plan

This expands SRS Section 11 into an executable, phase-by-phase plan. Each phase is scoped to be completed and verified independently, produces something runnable, and does not depend on any *later* phase — so they can be executed strictly in order with no rework.

Where the SRS left a decision open, it's resolved below (marked **Decision**) so no phase is blocked waiting on a judgment call. These are sensible, low-risk defaults for a solo, time-boxed build — revisit any of them later if needed.

---

## Phase 0 — Mesh Spike

**Goal:** Prove Mesh API connectivity before anything else is built on top of it — this is the make-or-break requirement, so it's de-risked first.

**Tasks**
- [x] `uv init`, add `openai`, `pydantic-settings`, `python-dotenv` as deps
- [x] `.env.example` with `MESH_API_KEY=` (done ahead of schedule, alongside `.gitignore`, while enabling CI checks)
- [x] `.gitignore` (must include `.env`, `.venv`, `__pycache__`, `*.db`) (done ahead of schedule, see above)
- [x] One throwaway script: one `embeddings.create` call + one `chat.completions.create` call through Mesh, printing the results — `scripts/mesh_spike.py`

**Decision:** confirmed real Mesh model identifiers empirically (docs list unreliable/possibly stale) — `sentence-transformers/all-minilm-l6-v2` for embeddings (384-dim, verified), `openai/chat-latest` for chat completions. Both live in `scripts/mesh_spike.py`; Phase 2's `LLMClient`/`embeddings.py` should reuse these unless a reason emerges to change them.

**You provide:** a valid Mesh API key (`rsk_...`) in your local `.env`. — Done.

**Definition of done:** script runs, both calls succeed, response is printed. ✅ Verified `uv run python scripts/mesh_spike.py` — embedding call returned a 384-dim vector, chat completion returned a coherent response. Nothing else depends on this script surviving — it's a spike, can be deleted once Phase 1 introduces the real `LLMClient`.

**Phase 0 status: ✅ Complete.**

---

## Phase 1 — Foundation

**Goal:** A running FastAPI app with auth, roles, and a page shell — no business features yet.

**Tasks**
- [x] Project structure per README (`app/`, `models/`, `routers/`, `services/`, `templates/`, `static/`) — `schemas/` deferred until a JSON API actually needs one (Phase 3); forms cover Phase 1's needs directly via FastAPI `Form(...)` params
- [x] `config.py` — pydantic-settings reading `.env` (`MESH_API_KEY`, `DATABASE_URL`, session secret, and the rest of `.env.example`)
- [x] `db.py` — SQLModel engine/session (SQLAlchemy under the hood), SQLite by default
- [x] `models/user.py` — `users` SQLModel table (FR-1)
- [x] Auth: register/login/logout via `passlib[bcrypt]`; session via Starlette `SessionMiddleware` (signed cookie — no separate session table needed for a solo build)
- [x] Role enforcement dependency (`user` vs `admin`) for route protection — `require_login`/`require_admin` in `app/services/auth.py`
- [x] Minimal Jinja2 base template + nav
- [x] Once `fastapi`/`sqlmodel` are added as dependencies, run `uvx library-skills --claude` to install their official AI agent skills into `.claude/skills/` (see [`AGENTS.md`](../AGENTS.md))
- [x] `Dockerfile` — containerize the FastAPI app (uv-based build)
- [x] `docker-compose.yml` — orchestrates the app + Qdrant (brought forward from Phase 2, since both are needed for a one-command dev environment) with a named volume for Qdrant storage and a bind-mounted SQLite data dir
- [x] `.dockerignore`
- [x] `Makefile` — standard entry points so the project is runnable without memorizing `uv`/`docker compose` invocations (renamed to `up`/`up-build`/`down`/`build`/`logs`/`ps` — see "Interim — Makefile rework" after Phase 2)

**Decisions:**
- Sessions are **signed-cookie based** (`SessionMiddleware`), not DB-backed — simplest option that satisfies FR-1.3 without an extra table.
- ORM is **SQLModel**, not raw SQLAlchemy — one class serves as both the DB table and the Pydantic schema, still SQLite → Postgres via `DATABASE_URL`. Database access stays **synchronous** (SQLModel supports async, but sync is simpler and adequate at hackathon scale/demo reliability).
- **Dockerized from Phase 1 onward**, not deferred to Phase 7 polish — the SRS explicitly values a frictionless "clone and run" reviewer experience (Sec. 2.1), and Qdrant already requires Docker for local dev (Sec 2.3/2.4), so wiring both the app and Qdrant into one `docker-compose.yml` now avoids doing this twice. The Qdrant service is defined now even though the app doesn't call it until Phase 2 — harmless to have running early.
- **Makefile added as the standard run interface** — wraps `uv`/`docker compose` commands rather than needing to know the underlying tool invocations. (Command names later revised — see "Interim — Makefile rework" after Phase 2.)
- Adopted **Library Skills** (`AGENTS.md`) for FastAPI/SQLModel — official, version-synced coding-agent guidance bundled directly with those packages; installed into `.claude/skills/` and refreshed on every upgrade. On Windows, symlink installation needs Developer Mode/admin (`WinError 1314`) — fall back to `--copy` (see `AGENTS.md`); installed skills are gitignored either way since they're regenerated from packages, not authored content.
- **Pinned `bcrypt<4.1`** — `passlib[bcrypt]`'s version-detection breaks against bcrypt ≥4.1 (`ValueError: password cannot be longer than 72 bytes` during passlib's own self-test, a known upstream incompatibility since passlib is unmaintained). Pinning is the standard workaround; revisit if passlib ever ships a fix, or consider dropping passlib for direct `bcrypt` use if this recurs.
- **Ruff configured with `extend-immutable-calls` for FastAPI's param functions** (`Depends`, `Query`, `Form`, etc.) — otherwise `ruff check` flags every dependency-injected route parameter as bug-prone (B008), which is a false positive for FastAPI's actual, required pattern. Documented, standard fix rather than scattering `# noqa` comments.
- **GNU Make installed via `winget install ezwinports.make`** for local Windows use — the Makefile itself is portable (works as-is in CI/WSL/Mac/Linux); this was just making `make` available on this dev machine.

**Definition of done:** ✅ Verified. Can register, log in, see a role-aware page, log out — confirmed via `pytest` (8/8 passing), manual curl flow, and browser-equivalent cookie-jar flow. `uv run uvicorn app.main:app --reload` serves it end to end. `docker compose build && docker compose up -d` also verified live: both containers start, `/`, `/admin` (redirects anonymous), and Qdrant's API all respond correctly, and a full register → session → home flow works against the containerized app with the SQLite file persisting correctly through the bind mount. `make lint`/`make test` confirmed working.

**Phase 1 status: ✅ Complete.**

---

## Phase 2 — Catalog + Dual-Write

**Goal:** Admin can manage products; every write lands in SQL *and* Qdrant, atomically. The catalog is seeded.

**Tasks**
- [x] `models/product.py` — `products` SQLModel table
- [x] `services/embeddings.py` — Mesh embeddings helper (batched, retry/backoff)
- [x] `services/vector_store.py` — Qdrant client, collection setup, upsert/delete by `product.id`, `get_indexed_ids`/`count` for resumability + verification
- [x] `services/llm_client.py` — the single `LLMClient` wrapper (promoted from the Phase 0 spike)
- [x] `services/catalog.py` — dual-write orchestration (`create_product`/`update_product`/`delete_product`), rolls back SQL on any Mesh/Qdrant failure (FR-2.5), raises `DualWriteError`
- [x] Admin CRUD routes/templates (`/admin/products`, create/edit/delete) — wired to `catalog.py`, shows a friendly error on `DualWriteError` instead of a raw 500
- [x] Public catalog browse/search/detail routes (`/catalog`, `/catalog/{id}`) — search by title/description, filter by category (FR-2.1)
- [x] `scripts/seed_catalog.py` — loads `scripts/data/courses.csv`, batches embeddings (~100/call), resumable (skips titles already in SQL), retry/backoff via `embeddings.py`
- [x] Local Qdrant via Docker — already covered by `docker-compose.yml` (Phase 1)

**Decisions:**
- **Dataset — changed from the SRS's originally-named sources.** Both the ~10k "Coursera/Udacity/Simplilearn/FutureLearn compilation" (primary) and the ~3.7k Udemy-courses set (fallback) were checked via the Kaggle API and came back `"licenses": [{"name": "unknown"}]` and `{"name": "other", ...license not specified at source}` respectively — not safe to redistribute in a public hackathon repo. Searched further (user-approved) and found a **CC0-1.0 (public domain)** family of 5 companion Udemy-category datasets from the same Kaggle uploader (`jilkothari`): IT & Software, Development, Business, Finance & Accounting, Lifestyle. Sampled 1,000 rows/category, deduped by title, interleaved round-robin across categories, and committed the result as `scripts/data/courses.csv` (5,000 rows, ~400KB, CC0-1.0 — freely redistributable, no attribution required). This is a genuine improvement over either originally-named source: cleanly licensed *and* better category diversity (5 real categories vs. the fallback's 4) for demonstrating behavioral clustering.
- **No `description` field in the source data** (title + price + rating + review/subscriber counts only — confirmed across all 5 category files). Mitigated two ways: Udemy titles are keyword-rich/SEO-optimized and carry more embedding signal than a bare product title would; `seed_catalog.py` also synthesizes a short enriched description from the real metadata fields (category, rating, review count) rather than embedding the title alone. Expected impact: coarse-grained clustering (the SRS's own "keeps landing on agentic-AI content" example) works fine; fine-grained nuance *within* one category is where a true prose description would have helped more.
- **`CATALOG_LIMIT` default stays 1,500** products, sliced as a prefix of the committed 5,000-row file — the file is deliberately larger than the working set (round-robin interleaved, so any prefix length stays category-balanced) so lifting the limit later needs no code change, matching SRS Sec. 9.1's intent.
- Prices are as scraped, in **INR** (all 5 source files are India-region Udemy data) — stored as a plain float per the SRS schema, no currency field/conversion invented.
- `Typer` for the seed script's CLI flags is an optional nicety, not core scope — add it only if plain `argparse`/hardcoded flags start feeling limiting.
- **Pinned Qdrant versions on both sides.** `qdrant/qdrant:latest` resolved to server 1.14.1, which the initially-installed `qdrant-client` (1.19.0) flagged as version-incompatible (major must match, minor diff ≤1). Rather than chase whatever `:latest` happens to be, pinned the image to `qdrant/qdrant:v1.14.1` (reproducibility - `:latest` silently drifting is its own risk) and `qdrant-client` to `>=1.14,<1.16` (resolved 1.15.1) to match. No more warning.
- **`seed_catalog.py` needs `sys.path` patched** — running it as `python scripts/seed_catalog.py` (the documented, SRS-matching invocation) only puts `scripts/` on `sys.path`, not the project root, so bare `app.*` imports fail. Fixed with an explicit `sys.path.insert(0, ...)` at the top of the script rather than changing the documented command to module form (`-m scripts.seed_catalog`).
- **Dockerfile `CMD` changed to `uv run --no-sync ...`** — plain `uv run` re-syncs the environment (including the `dev` dependency group: ruff, pytest) on every container start, adding ~15s and installing tools the running app never needs. Dependencies are already correct from the build-time `uv sync --no-dev` layers; `--no-sync` skips the redundant runtime check entirely.

**You provide:** Docker running locally (already satisfied via `make up`). Dataset sourcing no longer needs anything from you — it's committed to the repo.

**Definition of done:** ✅ Verified. `uv run python scripts/seed_catalog.py` run live against real Mesh + local Qdrant: 1,500/1,500 SQL↔Qdrant sync confirmed directly against both stores; re-running immediately confirmed resumability (all 1,500 skipped, "Nothing new to seed"). Admin dual-write verified live (not mocked): created a real product through `/admin/products/new` → Qdrant `points_count` 1500→1501 with a real Mesh embedding; deleted it → back to 1500. All 24 automated tests pass (`pytest`), `ruff check`/`format` clean. Full `docker compose build && up` verified: app + Qdrant both healthy, `/`, `/catalog`, `/catalog?category=...` all respond correctly through the container.

**Phase 2 status: ✅ Complete.**

---

## Interim — Makefile Rework & Manual Phase 1–2 Verification

Before starting Phase 3, per user request: reworked the Makefile's command names to the standard Docker Compose convention, and made Docker Compose the **sole supported way to run the project** (dropped the parallel "local `uv run uvicorn`" path from the README as a first-class option).

**Tasks**
- [x] Renamed Makefile targets to `up` / `up-build` / `down` / `build` / `logs` / `ps` (previously `docker-up` / `docker-build` / `docker-down` / `docker-logs`, no direct `up-build` equivalent existed)
- [x] `make seed` now runs **inside the running app container** (`docker compose exec app uv run --no-sync python scripts/seed_catalog.py`) instead of on the host — this was a latent bug: a host-run seed script writes to the host's `smartreco.db`, not the container's bind-mounted `/app/data/smartreco.db`, so the containerized app would never actually see the seeded data. Running it via `exec` guarantees it uses the exact same `DATABASE_URL`/`QDRANT_URL` the running app does.
- [x] README `Getting Started` rewritten around the single `make up-build && make seed` flow; dev tooling (`test`/`lint`/`fmt`) kept as local `uv run` commands since they don't touch the running app/DB at all (isolated in-memory DB, mocked Mesh/Qdrant)
- [x] Manual UI walkthrough of everything built in Phases 0–2 (see Decision below)
- [x] `scripts/create_admin.py` + `make create-admin` — interactive (email, password, confirm-password) admin creation, the only way to get an admin account

**Decisions:**
- **Docker Compose is now the only sanctioned way to run or manually test the project** (including for Claude Code itself, in this and future sessions) — no more switching between a local `uv run uvicorn` process and a containerized one. Reason: the two paths use different SQLite files by design (host path vs. container bind mount), which silently drifted out of sync during Phase 2 verification and is exactly the kind of split-brain state the project's own dual-write discipline is trying to avoid elsewhere. One path removes the ambiguity entirely.
- **Admins are never created via `/register`.** The public signup form has no role selector by design — self-service admin signup would be a privilege-escalation hole, and FR-1.2 only requires the two roles to exist and be enforced, not a specific bootstrap UX. `make create-admin` runs `scripts/create_admin.py` inside the container (same pattern as `make seed`, for the same DB-path-consistency reason): prompts for email, checks if that user already exists — if they do and aren't already admin, promotes them (no password re-entry, since the account already has one); if they do and already are admin, no-ops; otherwise prompts for password + confirmation and creates a fresh admin user. Verified live: fresh creation, promotion of an existing regular user, and idempotent no-op on an already-admin account all confirmed to log in and reach `/admin/products` correctly.

**Definition of done:** `make up-build` boots a clean stack; `make seed` populates it correctly; `make create-admin` covers all three cases (create/promote/no-op) correctly; a manual browser/curl walkthrough of registration, login, role-gated `/admin`, catalog browse/search/filter, and admin product CRUD all work against that single running stack.

---

## Interim — Design System & UI Pass (before Phase 3)

Before starting Phase 3, per user request: adopted a real design system (`docs/DESIGN.md`, generated via Stitch) and applied it to every template built in Phases 1–2, which had been bare unstyled HTML. This is a visual/UI-layer pass only — no Phase 3/4 business logic was added.

**Tasks**
- [x] `app/static/css/style.css` rewritten as CSS custom properties sourced from `docs/DESIGN.md`'s color/typography/spacing/radius/elevation tokens, plus a derived dark-mode palette (DESIGN.md only ships one palette; the dark variant reuses its `inverse-*`/`*-fixed-dim` tones)
- [x] Geist + Inter fonts loaded via Google Fonts in `base.html`
- [x] `app/services/ui.py::category_cover` — deterministic tonal cover + monogram for product cards, since the seeded dataset has no images (no schema/seed-script change; see Decision below)
- [x] Restyled: `base.html` (nav), `login.html`, `register.html`, `home.html`, `catalog/browse.html`, `catalog/detail.html`, `admin.html`, `admin/products_list.html`, `admin/product_form.html`
- [x] `catalog.py`'s `detail()` route gained a small `related` query (up to 3 other products in the same category) to power the "Related Courses" section
- [x] `app/routers/recommendations.py` (new) + `templates/recommendations/empty.html` — `GET /recommendations`, login-gated, always renders the cold-start empty state (true for every user until Phase 4's `Recommendation` model/agent exist); registered in `main.py`
- [x] Post-login/register redirect changed from `/` to `/catalog`; `/` now redirects authenticated visitors to `/catalog` and serves the marketing page only to anonymous ones
- [x] `tests/test_ui.py`, `tests/test_recommendations.py` added; `tests/test_auth.py` updated for the new redirect target and admin-page copy

**Decisions:**
- **Post-login lands on the Catalog, not Recommendations.** Recommendations can't exist without behavioral data (FR-4.1), so a brand-new user has nothing to show there; browsing the catalog is what generates the events the whole pipeline depends on. "My Recommendations" is a persistent nav tab, not the landing page.
- **No product images — generated tonal covers instead.** Sourcing real images (stock-photo API, Mesh image generation) would add an external dependency/cost never asked for in the SRS. `category_cover()` is pure, deterministic, and needs zero new infrastructure.
- **`/recommendations` added now, scoped to the empty state only.** Flagged explicitly rather than silently skipping ahead: the route/nav link exist today, but only ever render the cold-start state — no fake data, no agent dependency. Phase 4 extends this same router file with the real populated view.
- **Skill Level filter dropped** — not part of the SRS's `products` schema (FR-2.2); adding it would be an unflagged scope addition.
- **AI Suggestion sidebar box kept as a static placeholder** (generic copy, not real AI output) rather than removed — visually reserves its spot for Phase 4 without pretending to be functional.
- **Match-percentage badges (e.g. "98% Match") deferred to Phase 4, not added now** — but noted as *not* fabricated data: Qdrant already returns a real similarity score per retrieved point, so this can be a genuine number once retrieval exists.

**Definition of done:** `uv run ruff check` and `uv run pytest` pass (full suite); manual walkthrough — logged-out `/` → register → lands on `/catalog` (cover art renders, no Skill Level filter, AI box shows placeholder copy) → product detail (Related Courses shows) → `/recommendations` (empty state, links back to catalog) → admin `/admin/products` (styled table, cover thumbnails) → create/edit/delete still dual-writes correctly.

**Follow-up UI polish (same interim), per user feedback on the first pass:**
- **Nav bar hidden entirely until login.** `base.html`'s `<nav>` is now wrapped in `{% if user %}` — anonymous visitors (home, login, register, and anonymous catalog/detail browsing) see zero header chrome, matching the Stitch mockup's login screen exactly. Chosen deliberately over two more conservative options (keep a slim brand+login bar everywhere, or only drop nav on the 3 auth pages) — the tradeoff: anonymous catalog/detail pages now have no persistent way back to `/` or `/login` beyond in-page links, which is an accepted, explicit choice, not an oversight.
- **Real pagination** added to `/catalog` (`page` query param, `PAGE_SIZE=24`, truncated page-number list e.g. `1 … 4 5 6 … 63` via `_page_numbers()` in `catalog.py`) — the first pass only ever showed the first 24 products with no way to see the rest.
- **Working sort** (`sort` query param: recommended/newest/price ascending/price descending) and **category counts** in the filter sidebar (`select(Product.category, func.count(Product.id)).group_by(...)`), both real queries, not decorative.
- Added a decorative hero circle to the Catalog page and a hover-lift transition on product cards for closer visual parity with the Stitch reference.

---

## Interim — Docker Compose Hardening & Hot Reload (before Phase 3)

Before starting Phase 3, per user request: set up hot reload for local dev (code changes were requiring a full `make up-build` rebuild every time — `docker-compose.yml` only bind-mounted `./data`, not the app code, and the Dockerfile's `CMD` had no `--reload`), and made the Compose setup itself more clearly production-ready.

**Tasks**
- [x] `Dockerfile` — added a non-root `appuser` (created, `chown -R` on `/app`, `USER appuser` before `CMD`) and a `HEALTHCHECK` using Python's stdlib `urllib` (no curl/wget needed in the slim image)
- [x] `docker-compose.yml` — added `restart: unless-stopped`, healthchecks on both services (`app` via the same urllib probe; `qdrant` via its own `/readyz` endpoint, probed with bash's `/dev/tcp` since the official image ships no curl/wget — confirmed available: `bash`/`sh` present, verified live), `depends_on: qdrant: condition: service_healthy` (previously just waited for the container to *start*, not actually be ready), explicit `build.dockerfile`, and an `image:` tag for registry pushes
- [x] `docker-compose.override.yml` (new) — bind-mounts `./app` and `./scripts` and overrides `app`'s command to add `--reload`. Compose auto-merges this file whenever `docker-compose.yml` is loaded (no `-f` flag needed), so `make up`/`make up-build` get hot reload for free; committed to the repo (shared dev tooling, not a personal override)
- [x] `Makefile` — added `prod-build`/`prod-up`/`prod-down`, each passing `-f docker-compose.yml` explicitly to exclude the dev override (no bind mounts, no `--reload`) — this is the path a real deploy or CI/CD pipeline would use
- [x] `.env.example` — clarified that `DATABASE_URL`/`QDRANT_URL` are host-oriented defaults only (for anything run with bare `uv run` outside Docker); Compose always overrides both to their in-network values regardless of what `.env` says, since "localhost" inside the app container is the container itself, not the Qdrant container or the bind-mounted data directory
- [x] README's Getting Started section documents the hot-reload dev flow and the `prod-*` targets

**Decisions:**
- **`.env`'s `DATABASE_URL`/`QDRANT_URL` overrides in `docker-compose.yml` are intentional, not redundant.** They exist because `.env` has to serve two different contexts (host-run `uv` commands vs. the Docker Compose network) that can't share the same values — `localhost` means something different in each. This isn't something to "clean up" by deleting; it's the standard fix for that mismatch. Documented in both `.env.example` and `docker-compose.yml` itself so it doesn't look like an oversight again.
- **No official Docker Compose skill was available to use for this** — this project's Library Skills mechanism (`AGENTS.md`) only covers FastAPI and SQLModel (both tiangolo packages); Docker isn't a Python package and doesn't publish one through that channel. Applied standard, well-established Compose conventions by hand instead (base + auto-merged `override.yml` for dev, healthchecks, non-root user).
- **`docker-compose.override.yml` is committed**, not gitignored — it's meant as the team's shared default dev experience (auto-applied for everyone via `make up`), not an individual's personal-preference file, which is the other common convention for that filename.

**Definition of done:** `make up-build` rebuilds and starts the stack with hot reload; editing a router/template/CSS file under `app/` on the host is reflected immediately with no rebuild; `docker compose ps` shows both services healthy; `make prod-build`/`make prod-up` (explicit `-f docker-compose.yml`) start the exact same image with no bind mounts and no `--reload`, confirming the base file alone is deploy-ready.

---

## Phase 3 — Behavioral Tracking

**Goal:** Non-blocking frontend tracker + efficient backend ingestion. No AI yet — just clean data collection.

**Tasks**
- [x] `models/event.py` — `events` SQLModel table (`event_metadata`, not `metadata` — see Decision)
- [x] `static/js/tracker.js` — captures view/search/click/dwell; batches and flushes via `fetch(..., {keepalive: true})`, falling back to `sendBeacon` on page unload
- [x] `routers/events.py` — `POST /events`, Pydantic-validated batch (1–50 events), bulk-inserted in one transaction, plain 401 (not a page redirect) when unauthenticated
- [x] Wired into templates: `base.html` loads `tracker.js` only when logged in; search form gets `data-track-search`; product cards (`catalog/browse.html` and the related-courses section of `catalog/detail.html`) get `data-product-id`; the detail page's content root gets `data-track-view` for view+dwell

**Decisions:**
- Tracker flushes on **whichever comes first: 10 seconds of accumulated events, 20 events queued, or page unload** — bounds both latency (data isn't stale for long) and request volume (no per-click network call). Also acts as the "throttle high-frequency events" mechanism FR-3.2 asks for: nothing in this app currently produces genuinely high-frequency raw events (no live-search-as-you-type, no mousemove/scroll tracking), so batching *is* the throttle rather than needing a separate debounce on top of it.
- **Events only recorded for logged-in users**, not anonymous catalog browsing. The SRS's `events.user_id` is a non-null FK ("Who"), so there's no schema-valid way to store an anonymous event anyway — matches FR-4.1's premise that recommendations are built from a specific user's behavior.
- **`event_metadata`, not `metadata`, as both the Python attribute and the actual column name** — `metadata` is a reserved attribute on SQLAlchemy declarative models (`Base.metadata` is the schema registry itself), so a column literally named `metadata` raises `InvalidRequestError` on class definition. Documented pragmatic deviation from the SRS's literal column name for a hard technical constraint, not a design choice.
- **`/events` returns a plain 401 on missing auth, not `require_login`'s 303-redirect-to-`/login`.** `require_login` is designed for page navigation (a browser can follow a redirect); this endpoint is hit by `fetch()`/`sendBeacon` from JS, where a redirect response is meaningless — a clean 401 is what the tracker's `.catch()` (silently swallowed, tracking must never surface an error to the user) actually expects.
- **Found and fixed a real, severe bug from the previous session's Docker non-root-user hardening**, unrelated to tracking itself but blocking all manual verification: `appuser` (uid 1000, added for the container's runtime user) couldn't write to the bind-mounted `./data` directory, which keeps the *host* side's ownership (root, under Docker Desktop's Windows file-sharing layer) — the build-time `chown` on `/app/data` is irrelevant once the bind mount replaces that path at runtime. This broke `make up-build` for anyone, immediately, including a judge doing a fresh clone. Fixed with the standard pattern for this exact situation: `docker-entrypoint.sh` starts as root, `chown -R appuser:appuser /app/data` (now that the real mounted directory exists), then `exec gosu appuser "$@"` to drop privileges before running the actual command. Added `.gitattributes` (`*.sh`/`Dockerfile`/`docker-compose*.yml` forced to LF) alongside this, since a CRLF shebang line would silently break the new shell script on a Windows checkout.

**Definition of done:** ✅ Verified. 37/37 automated tests pass (event validation: auth required, batch stored correctly per type/metadata, oversized/empty/invalid-type batches rejected). Live verification against the real running stack (after fixing the Docker permission bug above): a real POST matching the tracker's exact request shape correctly created rows in `events` with the right `user_id`/`event_type`/`product_id`/`event_metadata`; confirmed `tracker.js` is served, present in the rendered HTML only when logged in (absent for anonymous visitors), and `data-track-search`/`data-product-id`/`data-track-view` all render with correct values. **Honest gap:** the client-side JS itself (event listeners, batch timing, `sendBeacon` on unload) is carefully code-reviewed and logically verified end-to-end via the backend calls it would make, but not executed in an actual browser JS engine — this environment has no browser/JS-runtime tool available to drive that directly.

**Phase 3 status: ✅ Complete** (pending your own quick real-browser spot-check of the JS, per the honest gap above).

---

## Phase 4 — Agent Core (RAG Pipeline)

**Goal:** The actual recommendation engine — behavioral profile → retrieval → grounded generation — wired end to end, callable manually.

**Tasks**
- [x] `models/recommendation.py` — `recommendations` SQLModel table
- [x] `services/vector_store.py::search` — top-K Qdrant semantic search (deferred from Phase 2, now actually needed)
- [x] `agent/nodes.py` — `build_profile` (recent events → category counts / repeated searches / dwell-seconds-by-category), `profile_to_query_text`, `retrieve_candidates` (Mesh embed + Qdrant top-K), `generate_narrative` (Mesh chat), `generate_recommendation` (full pipeline, returns `(narrative, product_ids)`)
- [x] `routers/recommendations.py` extended (the route already existed as a Phase-4-scaffolded empty state, from the PR #9 interim UI pass) — `GET /recommendations` now shows the latest stored recommendation if one exists, `POST /recommendations/refresh` runs the pipeline and stores a new one
- [x] `templates/recommendations/view.html` — narrative card + grounded product cards (reuses the existing `product-card`/`cover` styling), plus a small CSS addition (`.narrative-card`, `.recommendation-meta`)

**Decisions:**
- **A straight function chain, not a graph** — matches the Goal ("wired end to end, callable manually") and Phase 6's own framing (FR-4.5's LangGraph refactor is explicitly a *later*, additive bonus step: "refactor `agent/nodes.py` into an explicit `agent/graph.py` graph"). Building a graph now would be un-refactoring work for Phase 6 to redo.
- **`GET /recommendations` never calls Mesh/Qdrant** — it only reads the latest stored `Recommendation` row (or shows the cold-start empty state if none exists). Only `POST /refresh` runs the pipeline. This is ahead of Phase 5's formal trigger/cache layer, but there's no reason for a page *view* to ever cost an LLM call — Phase 5 adds the automatic-threshold trigger on top of this, not the "don't call Mesh on every view" discipline itself.
- **Display is always re-grounded against SQL at render time**, not trusted from the stored `product_ids` alone — `view_recommendations` re-fetches `Product` rows by ID and silently skips any ID no longer in the catalog (e.g. a product deleted after the recommendation was generated), rather than crashing or rendering a broken card. Order is preserved from the agent's ranking (`.in_()` doesn't guarantee row order).
- **`trigger_reason` defaults to `"manual"`** — Phase 4 only has the manual refresh button; Phase 5 introduces the `"threshold"` auto-trigger path onto the same field.
- **Match-percentage badges still not added**, despite PR #9's interim notes flagging Qdrant's real similarity score as available for this. Displaying it live (right after a refresh) is easy, but showing it consistently on every later page *view* would require either persisting scores (a schema field beyond the SRS's `product_ids`-only spec) or recomputing them on every view (defeats the "no Mesh/Qdrant call on GET" decision above). Left out rather than doing either half-measure; revisit if a later phase gives it a natural home.

**Definition of done:** ✅ Verified. 47/47 automated tests pass (profile aggregation from events, query-text formatting, retrieval/generation with mocked Mesh+Qdrant, router flows including the stale-product-id skip case). **Live, end-to-end, against the real running stack — no mocks:** registered a test user, generated real view/click/dwell/search events on real seeded products (Python/Development-related), hit `POST /recommendations/refresh` (~6s — real Mesh embedding + real Qdrant top-K + real Mesh chat generation), and got back a coherent narrative that correctly referenced the actual behavioral signals ("you've consistently focused on Development and specifically searched for 'python for data science'"), recommending 5 courses — every one of them genuinely Python/data-related, and **all 5 confirmed to exist as real rows in the `products` table** (zero hallucination). Confirmed `GET /recommendations` is fast (93ms vs. the refresh's 6.2s) — no LLM call on a page view. Confirmed a brand-new user with zero events still correctly gets the cold-start empty state, unaffected. Full `docker compose build` from scratch also verified healthy (not just hot-reloaded).

**Follow-up fix #1 (same day, found via the user's own real-browser testing):** the cold-start empty state (`recommendations/empty.html`) only ever linked back to `/catalog` — there was no button anywhere in the UI that actually `POST`s to `/recommendations/refresh` unless a recommendation already existed. A user could browse extensively, generating real events, and still see the empty state forever, because nothing ever triggered the first generation. (My own live verification above didn't catch this because I drove `POST /refresh` directly via `curl`, never through the actual UI path a browser click would take — a gap in *how* I verified, not just what.) Fixed: `view_recommendations` checked whether the user had any tracked `Event`, showing a primary "Generate My Recommendations" button when they did. Superseded by follow-up #2 below the same day.

**Follow-up fix #2 (same day, per user feedback on fix #1):** the button from fix #1 still required an extra click before seeing anything, for a state (real behavior, no recommendation yet) where there's no actual reason to wait for one. Changed to: `GET /recommendations` now auto-generates and stores the first recommendation inline, the very first time a user with tracked activity visits the page — no button, no extra click. Implementation: extracted `_generate_and_store()` (shared by this path and `POST /refresh`) and `_has_activity()`; `empty.html` reverted to its simple original form, since it's now only ever reached by users with genuinely zero activity (nothing to generate from). This does mean `GET` can occasionally cost a real Mesh/Qdrant call now — narrowing, not reversing, the earlier "`GET` never calls Mesh" decision: it still holds once a recommendation exists (the overwhelming majority of visits), it just doesn't hold for the one-time transition into having one. `trigger_reason` stays `"manual"` for this case — the SRS only defines `"manual"`/`"threshold"`, and a self-initiated first visit is closer in spirit to the former than to Phase 5's event-count auto-trigger.

Reverified live against the real stack both times: fix #1 confirmed the button appeared and worked; fix #2 confirmed a single visit (no click) now produces a real, grounded recommendation directly (~6.8s, matching the generation cost, vs. 268ms on the next visit — confirming no regeneration), and that a genuinely zero-activity user is unaffected.

**Follow-up fix #3 (same day, per user feedback on fix #2):** fix #2's single visit still made the user wait ~6-7s on a blank tab with zero feedback before the page rendered at all — the auto-generate improved *whether* the user had to click, not *how it felt* to wait. User explicitly asked about streaming as an option. Implemented real narrative streaming:
- `LLMClient.chat_stream()` (`stream=True` on the Mesh chat call, an OpenAI-compatible passthrough) yields text deltas instead of waiting for the full completion.
- Split `agent/nodes.py`'s pipeline: `prepare_candidates()` (the fast part — one Mesh embed call + Qdrant top-K, ~1-3s) is now separable from `generate_narrative_stream()` (the slower part, now incremental). `generate_recommendation()` (used by `POST /refresh`) is unchanged, composing both in sequence as before.
- `GET /recommendations`, on a user's first visit with activity, now runs retrieval only and renders a new `recommendations/generating.html` immediately — real grounded product cards visible right away, with a pulsing "Thinking about what fits you best…" placeholder for the narrative.
- New `GET /recommendations/stream` (Server-Sent Events): re-derives the profile (cheap, DB-only, no Mesh call) and streams the narrative for the exact candidate IDs the page already rendered — **does not re-embed or re-query Qdrant**, avoiding a duplicate Mesh cost. `app/static/js/recommendations-stream.js` (`EventSource`, matching the `tracker.js` pattern of a dedicated static file) appends each chunk to the narrative element as it arrives, then persists via the same `_store_recommendation()` helper once the stream's `done` event fires.
- **Scoped to the first-generation path only** — `POST /refresh` (used when a recommendation already exists, so the user has visible content and a clear "I clicked something" expectation) deliberately keeps its simple synchronous-then-redirect pattern; streaming there would need the refresh button to become JS-driven too, for a case that's less jarring to begin with.

Reverified live: retrieval-only page render dropped to ~2-3s after container warm-up (down from the full ~6-7s), with real grounded product cards visible immediately; the narrative then streamed as 5 distinct SSE chunks (confirmed via raw `curl -N`, not just the browser), completing in under a second once retrieval had already run; the finished narrative persisted correctly (full text reassembled from chunks, correct `product_ids`); a follow-up visit correctly served the stored recommendation via the normal fast path, no regeneration. 51/51 tests passing.

**Follow-up fix #4 (found by the user immediately after, real production traceback):** fix #3's `chat_stream()` crashed with `IndexError: list index out of range` at `chunk.choices[0]` — Mesh's streaming API sends at least one chunk with an **empty `choices` list** (a common OpenAI-compatible streaming pattern, e.g. a trailing usage/metadata chunk that carries no token delta), which an unconditional index into `choices[0]` doesn't survive. Since this happened inside the SSE generator with no error handling around it, the crash killed the whole stream mid-generation — the narrative never finished, nothing got persisted, and the user was left stuck watching a placeholder that would never resolve. Two-part fix:
- **Root cause:** `chat_stream()` now skips any chunk with an empty `choices` list before indexing into it, instead of assuming every chunk carries a token delta.
- **Defense in depth:** wrapped the SSE generator's streaming loop in the router so *any* unexpected failure degrades gracefully instead of crashing the connection — if content already streamed before a late failure, it's still persisted (better than losing real output and leaving the user stuck); if nothing streamed yet, a distinct `event: failed` SSE frame tells the client to show a retry message. (Deliberately not named `event: error` — that collides with `EventSource`'s own built-in connection-error event, an inconsistent-across-browsers gotcha; `recommendations-stream.js` listens for `failed` separately from its `onerror` connection-level handler.)

Added a direct regression test for `chat_stream()` reproducing the exact empty-choices scenario, plus two new SSE-endpoint tests (immediate failure -> `failed` event + no orphan row persisted; failure-after-partial-content -> partial narrative persisted). Reverified live against the real stack: the exact request that crashed before now completes in well under a second with no errors in the logs, repeated 3 times back-to-back with no failures, and the recommendation persists correctly each time. 54/54 tests passing.

**Phase 4 status: ✅ Complete.**

---

## Phase 5 — Triggers + Caching

**Goal:** Stop calling the LLM on every action — make regeneration meaningful and efficient (this is explicitly judged: NFR "Efficiency").

**Tasks**
- [ ] `agent/triggers.py` — hybrid trigger: auto-fires once **N new qualifying events** have accumulated since the last recommendation, OR the user hits manual refresh
- [ ] Caching: if the trigger hasn't fired, serve the stored `recommendations` row instead of calling Mesh
- [ ] `trigger_reason` field populated (`threshold` / `manual`) for observability

**Decision:** **N = 5 new qualifying events** (view/search/click/dwell-over-threshold count equally) triggers auto-regeneration. This is frequent enough to feel responsive in a live demo, infrequent enough to keep Mesh usage bounded and clearly "meaningful," and manual refresh always remains available regardless of count. Tune later if demo behavior warrants it — it's a single constant.

**Definition of done:** generating recommendations repeatedly without new activity costs zero additional Mesh calls (verified via logs/LangSmith); crossing the 5-event threshold auto-regenerates.

---

## Phase 6 — Bonuses

**Goal:** Layer the committed bonus scope onto the now-working core pipeline.

**Tasks**
- [ ] **LangGraph (FR-4.5):** refactor `agent/nodes.py` into an explicit `agent/graph.py` graph — analyze → decide-to-retrieve → evaluate retrieval quality → refine-if-weak → generate
- [ ] **APScheduler (FR-6):** `scheduler.py` — in-process daily job that runs the same agent pipeline per active user and emails the digest
- [ ] **Email delivery:** `services/email.py` sending via SMTP (`smtplib`), configured through `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`DIGEST_FROM_EMAIL` env vars
- [ ] **LangSmith (FR-7):** tracing enabled via env vars (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`) around the agent graph — no code-path branching needed, it's instrumentation-only
- [ ] **Metadata filtering:** extend Qdrant retrieval to optionally filter by `category`/`price` payload fields

**Decision:** email digest is sent via **plain SMTP**, not a paid provider — zero added cost/dependency, fits the "no extra broker/service" philosophy already used for APScheduler. If `SMTP_*` env vars are unset (e.g. during CI or a reviewer's clone-and-run), the digest job **logs the rendered email to console/file instead of sending** — so the scheduled job never crashes a demo for lack of mail credentials, and the feature is still visibly exercised.

**You provide (optional):** real SMTP credentials (e.g. a Gmail App Password or any SMTP relay) if you want actual emails during your own testing; not required for the app to run or demo.

**Definition of done:** LangGraph run visible in LangSmith with all steps traced; a manually-triggered digest run produces a correctly rendered email (sent or logged); category-filtered retrieval returns narrower results than unfiltered.

---

## Phase 7 — Polish + Submit

**Goal:** Everything the CI screener and human judges need to find, present and correct.

**Tasks**
- [ ] Finalize `README.md` (setup steps verified from a clean clone, bonus features called out, catalog scope stated explicitly per Sec. 9.1 — already drafted, revisit once code exists)
- [ ] `.env.example` complete and accurate
- [ ] Confirm `.gitignore` excludes `.env`, `.venv`, `*.db`, `__pycache__`
- [ ] Download the mandated CI workflow **only** from the official hackathon dashboard → `.github/workflows/smartreco-checks.yml`
- [ ] Set GitHub repo secrets: `MESH_API_KEY`, `SUBMISSION_TOKEN`
- [ ] `requirements.txt` (exported from `uv`) lists `fastapi` + `openai` explicitly, for the automated screener
- [ ] Sanity pass: fresh clone → `uv sync` → seed → run, following only the README
- [ ] Optional: deploy (Qdrant Cloud free tier + Postgres) and record a short demo video

**Definition of done:** a reviewer can clone the repo cold and have it running locally following only the README; CI checks (critical + advisory) pass.

---

## Sequencing Notes

- Phases are **strictly sequential** — each assumes the previous phase's tables/services already exist. Don't start Phase *N* until Phase *N-1*'s definition of done is met.
- Phase 0 is disposable scaffolding; everything from Phase 1 onward is the real app.
- Bonuses (Phase 6) are intentionally last — the core judged loop (Phases 1–5) is a complete, submittable product on its own if time runs out before Phase 6/7 finish.
- Blockers that need something from you specifically: **Mesh API key** (Phase 0), **Docker + dataset file** (Phase 2), **CI workflow file from the hackathon dashboard + repo secrets** (Phase 7). Nothing else in the plan is blocked on external input.
