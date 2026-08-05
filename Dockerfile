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

# gosu: lets the entrypoint start as root (needed to fix bind-mount
# ownership below), then drop to appuser before exec'ing the real process -
# the standard pattern for "non-root user + a bind-mounted volume".
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# The app never needs root once running - only /app/data needs to be owned
# by this user (it's where the bind-mounted SQLite file lives and must stay
# writable). Actual ownership of the *mounted* directory is fixed at
# container start by docker-entrypoint.sh, not here - see that file for why
# a build-time chown alone isn't enough.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data

EXPOSE 8000

# No extra tool (curl/wget) needed for the healthcheck — Python's already here.
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://localhost:8000/', timeout=3)"]

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# --no-sync: dependencies are already correct from the build steps above;
# skip re-checking/re-syncing (incl. dev deps) on every container start.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
