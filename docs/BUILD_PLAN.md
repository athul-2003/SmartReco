# SmartReco — Phased Build Plan

This expands SRS Section 11 into an executable, phase-by-phase plan. Each phase is scoped to be completed and verified independently, produces something runnable, and does not depend on any *later* phase — so they can be executed strictly in order with no rework.

Where the SRS left a decision open, it's resolved below (marked **Decision**) so no phase is blocked waiting on a judgment call. These are sensible, low-risk defaults for a solo, time-boxed build — revisit any of them later if needed.

---

## Phase 0 — Mesh Spike

**Goal:** Prove Mesh API connectivity before anything else is built on top of it — this is the make-or-break requirement, so it's de-risked first.

**Tasks**
- [ ] `uv init`, add `openai`, `pydantic-settings`, `python-dotenv` as deps
- [ ] `.env.example` with `MESH_API_KEY=`
- [ ] `.gitignore` (must include `.env`, `.venv`, `__pycache__`, `*.db`)
- [ ] One throwaway script: one `embeddings.create` call + one `chat.completions.create` call through Mesh, printing the results

**You provide:** a valid Mesh API key (`rsk_...`) in your local `.env`.

**Definition of done:** script runs, both calls succeed, response is printed. Nothing else depends on this script surviving — it's a spike, can be deleted once Phase 1 introduces the real `LLMClient`.

---

## Phase 1 — Foundation

**Goal:** A running FastAPI app with auth, roles, and a page shell — no business features yet.

**Tasks**
- [ ] Project structure per README (`app/`, `models/`, `schemas/`, `routers/`, `services/`, `templates/`, `static/`)
- [ ] `config.py` — pydantic-settings reading `.env` (`MESH_API_KEY`, `DATABASE_URL`, session secret)
- [ ] `db.py` — SQLModel engine/session (SQLAlchemy under the hood), SQLite by default
- [ ] `models/user.py` — `users` SQLModel table (FR-1)
- [ ] Auth: register/login/logout via `passlib[bcrypt]`; session via Starlette `SessionMiddleware` (signed cookie — no separate session table needed for a solo build)
- [ ] Role enforcement dependency (`user` vs `admin`) for route protection
- [ ] Minimal Jinja2 base template + nav
- [ ] Once `fastapi`/`sqlmodel` are added as dependencies, run `uvx library-skills --claude` to install their official AI agent skills into `.claude/skills/` (see [`AGENTS.md`](../AGENTS.md))

**Decisions:**
- Sessions are **signed-cookie based** (`SessionMiddleware`), not DB-backed — simplest option that satisfies FR-1.3 without an extra table.
- ORM is **SQLModel**, not raw SQLAlchemy — one class serves as both the DB table and the Pydantic schema, still SQLite → Postgres via `DATABASE_URL`. Database access stays **synchronous** (SQLModel supports async, but sync is simpler and adequate at hackathon scale/demo reliability).
- Adopted **Library Skills** (`AGENTS.md`) for FastAPI/SQLModel — official, version-synced coding-agent guidance bundled directly with those packages; installed into `.claude/skills/` and refreshed on every upgrade.

**Definition of done:** can register, log in, see a role-aware page, log out. `uv run uvicorn app.main:app --reload` serves it end to end.

---

## Phase 2 — Catalog + Dual-Write

**Goal:** Admin can manage products; every write lands in SQL *and* Qdrant, atomically. The catalog is seeded.

**Tasks**
- [ ] `models/product.py` — `products` SQLModel table
- [ ] `services/embeddings.py` — Mesh embeddings helper (batched)
- [ ] `services/vector_store.py` — Qdrant client, collection setup, upsert/delete by `product.id`
- [ ] `services/llm_client.py` — the single `LLMClient` wrapper (promoted from the Phase 0 spike)
- [ ] Admin CRUD routes/templates (create/edit/delete products) — dual-write wrapped so a Mesh/Qdrant failure rolls back the SQL write (FR-2.5)
- [ ] Public catalog browse/search/detail routes (FR-2.1)
- [ ] `scripts/seed_catalog.py` — loads dataset, batches embeddings (~100/call), resumable (skip existing Qdrant points), light retry/backoff on rate limits
- [ ] Local Qdrant via `docker run -p 6333:6333 qdrant/qdrant`

**Decisions:**
- **Dataset:** Kaggle online-courses compilation (Coursera/Udacity/Simplilearn/FutureLearn, ~10k rows) as primary source; the ~3.7k Udemy-courses dataset as fallback if the primary is unavailable/license-blocked at build time.
- **`CATALOG_LIMIT` default: 1,500** products — midpoint of the SRS's 1,000–2,000 working-set range, config-flag-driven so it's a one-line change either direction.
- `Typer` for the seed script's CLI flags is an optional nicety, not core scope — add it only if plain `argparse`/hardcoded flags start feeling limiting.

**You provide:** Docker running locally; the chosen dataset CSV placed where the seed script expects it.

**Definition of done:** `uv run python scripts/seed_catalog.py` populates SQLite + Qdrant with ~1,500 products; admin CRUD keeps both stores in sync (verified by editing/deleting a product and checking both stores).

---

## Phase 3 — Behavioral Tracking

**Goal:** Non-blocking frontend tracker + efficient backend ingestion. No AI yet — just clean data collection.

**Tasks**
- [ ] `models/event.py` — `events` SQLModel table
- [ ] `static/js/tracker.js` — captures view/search/click/dwell; throttles/debounces high-frequency events; batches and flushes via `fetch(..., {keepalive: true})` (falls back to `sendBeacon` on page unload)
- [ ] `routers/events.py` — ingestion endpoint accepting a batch, validated via Pydantic, bulk-inserted
- [ ] Wire the tracker into catalog/detail/search templates

**Decision:** tracker flushes on **whichever comes first: 10 seconds of accumulated events, 20 events queued, or page unload** — bounds both latency (data isn't stale for long) and request volume (no per-click network call).

**Definition of done:** browsing the catalog generates rows in `events` without any perceptible UI lag; a network throttling check confirms tracking doesn't block page interaction.

---

## Phase 4 — Agent Core (RAG Pipeline)

**Goal:** The actual recommendation engine — behavioral profile → retrieval → grounded generation — wired end to end, callable manually.

**Tasks**
- [ ] `models/recommendation.py` — `recommendations` SQLModel table
- [ ] `agent/nodes.py` — profile-building (recent events → interests/categories/repeated searches), Mesh embed of the profile query, Qdrant top-K retrieval, Mesh chat generation of narrative + product list
- [ ] `routers/recommendations.py` — endpoint to view current recommendation + a manual "refresh" action
- [ ] Recommendation display template (narrative + grounded product cards)

**Definition of done:** for a user with tracked events, hitting "refresh" produces a stored, displayed recommendation whose products are all real catalog items (verifiable by ID lookup — never hallucinated).

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
