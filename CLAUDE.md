# CLAUDE.md

Instructions for Claude Code (and any contributor) working in this repository.

## Project Context

SmartReco is a behavioral AI recommendation platform built for the SmartReco Build Challenge 2026, with every AI call routed through Mesh API. Before doing any work, be familiar with:

- [`README.md`](README.md) — project overview, architecture, tech stack.
- [`docs/SmartReco_SRS.docx`](docs/SmartReco_SRS.docx) — the source Software Requirements Specification. Requirement IDs (FR-1, FR-2, ...) referenced anywhere in code or commits trace back to this document.
- [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) — the phase-by-phase execution plan. **This is the authoritative task list — do not invent scope outside it without flagging the addition to the user first.**

## How to Execute Phases

1. Work **one phase at a time**, strictly in the order defined in `docs/BUILD_PLAN.md`. Do not start Phase *N+1* until Phase *N* has been merged to `main`.
2. Before starting a phase, re-read its section in `BUILD_PLAN.md` — tasks, decisions already made, and its Definition of Done.
3. Check off tasks in `BUILD_PLAN.md` as they're completed within the phase (keep the checklist honest — it's the project's real progress tracker).
4. If a phase surfaces an ambiguity the SRS doesn't resolve, make the pragmatic call yourself (matching the precedent already set in `BUILD_PLAN.md`'s "Decision" callouts) and record what was decided and why in the PR description — don't block the phase on it unless it's a genuinely consequential, hard-to-reverse choice.
5. A phase is not "done" until its Definition of Done in `BUILD_PLAN.md` is met, its tests pass (see below), and it's merged to `main` via PR.
6. Don't bundle multiple phases into one branch/PR. One phase = one branch = one PR (a phase can be split into more than one PR if it's large, but never merge phases together).

## Testing Requirements

Every phase has both automated and manual verification. Do not open a PR until both are done.

**General rules:**
- All new business logic under `app/services/` and `app/agent/` needs `pytest` coverage of its critical paths — not 100% coverage for its own sake, but every non-trivial branch (success path, the main failure path, edge cases called out in the SRS like dual-write rollback).
- **Never** hit real paid/external APIs (Mesh, Qdrant, SMTP) from automated tests — mock them. Real calls are for manual verification and the Phase 0 spike only.
- Run the **full** test suite before every commit that touches application code, not just tests for what you just changed.
- Never commit code with failing tests. If a test can't pass yet because of incomplete work, don't commit that slice — finish it or revert.

**Per-phase minimum bar** (see `docs/BUILD_PLAN.md` for full task lists):

| Phase | Automated | Manual |
|---|---|---|
| 0 — Mesh spike | — | Run the spike script; confirm both an embedding call and a chat call return successfully. |
| 1 — Foundation | pytest: register/login/logout, role-enforcement on a protected route | Browser check: protected admin route rejects a regular user. |
| 2 — Catalog + dual-write | pytest: create/edit/delete keeps SQL + Qdrant in sync; simulated Mesh failure rolls back the SQL write | Run `seed_catalog.py`; confirm row counts match between SQLite and Qdrant. |
| 3 — Tracking | pytest: event validation + batch insert | DevTools network tab: confirm tracking never blocks page interaction; batching/throttling behaves as configured. |
| 4 — Agent core | pytest: pipeline stages with mocked Mesh/Qdrant | Confirm every recommended product ID exists in the catalog (no hallucinated products). |
| 5 — Triggers + cache | pytest: trigger fires at the configured threshold and not before; cache hit makes zero additional mocked Mesh calls | Manually cross the threshold in a test account; confirm auto-regeneration. |
| 6 — Bonuses | pytest: scheduler job logic invoked directly (no need to run the real scheduler loop in tests); metadata-filter query narrows results | Inspect a LangGraph run in LangSmith; manually trigger the digest job and confirm output (sent or logged). |
| 7 — Polish + submit | CI workflow passes | Fresh clone → `uv sync` → seed → run, following **only** the README. |

## Git & Branching Workflow

`main` is protected — no direct commits to `main`, ever, including "just a quick fix."

**Starting any phase or task:**
```bash
git checkout main
git pull origin main
git checkout -b phase-<N>-<short-description>   # e.g. phase-2-catalog-dual-write
```
Branch naming: `phase-<N>-<description>` for build-plan phases, `fix/<description>` for bugfixes, `chore/<description>` for non-feature work (deps, tooling, docs).

**Committing:**
- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`. Imperative mood ("add dual-write rollback", not "added" or "adds").
- Commit in logically separable chunks as work progresses — not one giant commit at the end of a phase.
- Before every commit: check `git status` / `git diff` for anything that shouldn't be there — especially `.env`, credentials, or generated DB files. `.gitignore` is the backstop, not the check itself.
- Never use `--no-verify`, `--no-gpg-sign`, or amend/rewrite history on anything already pushed.

**Opening a PR:**
```bash
git push -u origin phase-<N>-<short-description>
gh pr create --title "..." --body "..."
```
- Every branch merges to `main` via PR — never a direct merge/push to `main`, even solo.
- PR description covers: what changed, which phase/FR it satisfies, how it was tested (automated + manual, per the table above), and any SRS ambiguity resolved along the way.
- Wait for CI to pass before merging (CI exists from Phase 7 onward; before that, treat "all tests pass locally" as the equivalent gate).
- **Standing authorization:** open the PR and, once its Definition of Done is met and checks pass, merge it to `main` without waiting for a separate per-merge confirmation — the user has pre-approved this as the normal per-phase workflow. Still pause and check in if something in the PR is a genuine surprise (e.g. a check is failing and the fix isn't obvious, or the phase's scope grew beyond what `BUILD_PLAN.md` describes).
- Prefer "squash and merge" for a clean, one-commit-per-feature `main` history. Delete the branch after merge.

## Industry-Standard Practices

- **Secrets:** only ever in `.env` (gitignored) and GitHub Actions repository secrets. Never hardcoded, never logged, never pasted into a commit message or PR description.
- **Dependencies:** managed via `uv`; commit `uv.lock` so builds are reproducible. Keep `.env.example` in sync with every new required environment variable, the moment it's introduced.
- **Style:** `ruff` for linting and formatting, run before every commit. Type hints on public functions; Pydantic models at every request/response and external-API boundary.
- **Comments/docstrings:** only where the *why* isn't obvious from the code (matches the SRS's Maintainability NFR) — no restating what a function does in prose.
- **Logging:** structured logging (`logging` module), never bare `print()` in application code.
- **PR size:** small and focused — one phase (or one sub-task of a large phase) per PR. If a phase's diff is getting large enough to be hard to review, split it.
- **README/`.env.example` upkeep:** update at the end of every phase if setup steps or required env vars changed — don't let docs drift from what the code actually needs.
- **Migrations:** once the schema stabilizes past initial dev iteration, introduce Alembic migrations rather than relying on `create_all` — keeps the SQLite → Postgres path (already promised in the SRS) honest.

## Definition of Done — Every Phase, Before Opening a PR

1. All tasks for the phase in `docs/BUILD_PLAN.md` checked off.
2. Automated tests written and passing locally (full suite, not just new tests).
3. Manual verification steps for the phase completed (see table above).
4. `git diff`/`git status` checked — no secrets, no stray files.
5. `README.md` and `.env.example` updated if this phase changed setup steps or added env vars.
6. Branch pushed, PR opened against `main` with a description covering what/why/how-tested.
