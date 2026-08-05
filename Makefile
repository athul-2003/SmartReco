.PHONY: help install run test lint fmt seed docker-build docker-up docker-down docker-logs clean

help:
	@echo "SmartReco - available commands:"
	@echo "  make install       Install dependencies (uv sync)"
	@echo "  make run           Run the app locally with auto-reload"
	@echo "  make test          Run the test suite"
	@echo "  make lint          Lint app/scripts/tests with ruff"
	@echo "  make fmt           Format app/scripts/tests with ruff"
	@echo "  make seed          Seed the catalog (DB + Qdrant) - available from Phase 2"
	@echo "  make docker-build  Build the app + Qdrant images"
	@echo "  make docker-up     Start the full stack (app + Qdrant) in the background"
	@echo "  make docker-down   Stop the full stack"
	@echo "  make docker-logs   Tail logs from the running stack"
	@echo "  make clean         Remove caches and local DB files"

install:
	uv sync

run:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest -v

lint:
	uv run ruff check app scripts tests

fmt:
	uv run ruff format app scripts tests

seed:
	uv run python scripts/seed_catalog.py

docker-build:
	docker compose build

docker-up:
	docker compose up -d
	@echo "App:    http://localhost:8000"
	@echo "Qdrant: http://localhost:6333/dashboard"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
	rm -f smartreco.db
