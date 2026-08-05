FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Install dependencies first, in their own layer, so code edits don't bust the cache.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY . .
RUN uv sync --locked --no-dev

# Run as a non-root user in production — the image never needs root at runtime.
# Only /app/data needs to be owned by this user (it's where the bind-mounted
# SQLite file lives and must stay writable); the code + venv are read/execute
# only, and COPY's default permissions already allow that for non-owners, so
# chowning the whole tree would just be a slow no-op.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data
USER appuser

EXPOSE 8000

# No extra tool (curl/wget) needed for the healthcheck — Python's already here.
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://localhost:8000/', timeout=3)"]

# --no-sync: dependencies are already correct from the build steps above;
# skip re-checking/re-syncing (incl. dev deps) on every container start.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
