# AGENTS.md

Official, version-synced AI agent skills available to this project via [Library Skills](https://library-skills.io).

## What this is

FastAPI and SQLModel (both maintained by tiangolo — SmartReco's two core Python dependencies per the [Tech Stack](README.md#tech-stack)) each ship an **official AI coding-agent skill bundled with the package itself**. Instead of an agent relying on stale training data, these skills are installed straight from the library's own distribution, so the guidance always matches the exact version pinned in this project's `pyproject.toml` / `uv.lock`.

- FastAPI skill: bundled with the `fastapi` package
- SQLModel skill: bundled with the `sqlmodel` package (confirmed at `sqlmodel.tiangolo.com/install/#ai-agent-skills`)

Installer tool: `library-skills` (run via `uvx`, so no separate install step). It scans this project's dependencies, finds which installed libraries publish a skill, and installs each as a **symlink** into the target skills directory — meaning `uv sync`/`uv lock` upgrades a library and the skill content updates right along with it, with no manual re-fetch step.

## Install / refresh

Run from the repo root, once `fastapi` and `sqlmodel` are real dependencies (i.e. from Phase 1 of `docs/BUILD_PLAN.md` onward):

```bash
uvx library-skills --claude --all --yes
```

The `--claude` flag installs into `.claude/skills/` (Claude Code's expected location, alongside the generic `.agents/skills/` other tools use). `--all --yes` skips the interactive picker, which doesn't render in a non-TTY/CI shell.

**Windows note:** creating the skills as symlinks requires a privilege Windows doesn't grant by default (Developer Mode or admin). If you hit `WinError 1314`, add `--copy` to install real file copies instead:

```bash
uvx library-skills --claude --all --yes --copy
```

The trade-off: copied files don't auto-update when `fastapi`/`sqlmodel` is upgraded (symlinks would) — **re-run this command any time either is upgraded**, on any OS, so installed content stays aligned with the version actually in use.

Installed skills are **not committed** — `.agents/` and `.claude/skills/` are gitignored, since they're fully regenerated from installed packages via the command above (same reasoning as not committing `.venv/`).

## What this enables

Once installed, the FastAPI and SQLModel skills are ordinary Claude Code Skills — discoverable and invokable via the `Skill` tool like any other skill in this environment. Reach for them (or let Claude reach for them automatically when relevant) when:

- Defining or refactoring **SQLModel** table/schema classes (`app/models/`) — table vs. non-table models, relationships, `Field`/`Relationship` usage, the SQLAlchemy-under-the-hood details SQLModel abstracts.
- Writing or reviewing **FastAPI** routers, dependencies, request/response models, or app wiring (`app/routers/`, `app/main.py`) — current idioms for dependency injection, `Depends`, lifespan events, response models, etc.

This is guidance and reference material, not a replacement for `docs/BUILD_PLAN.md` (the mandatory task sequence) or `docs/SmartReco_SRS.docx` (the source of truth for requirements) — use it to implement *how* a phase's FastAPI/SQLModel code is written correctly, not to decide *what* to build.

## Supported libraries

Per Library Skills' own listing, FastAPI and Streamlit currently publish official skills, and SQLModel does as well (confirmed directly from its docs). SmartReco doesn't use Streamlit. If **Typer** is adopted later (it's an optional nicety floated in `docs/BUILD_PLAN.md` Phase 2 for the seed script's CLI) it's worth re-checking whether it has since joined this list, since it's also a tiangolo project.
