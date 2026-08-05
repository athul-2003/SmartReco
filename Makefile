.PHONY: help install build up up-build down logs ps seed test lint fmt clean

help:
	@echo "SmartReco - available commands:"
	@echo ""
	@echo "  Running the app (Docker Compose - the only supported way to run the project):"
	@echo "  make up            Start the full stack (app + Qdrant) in the background"
	@echo "  make up-build      Rebuild the app image, then start the full stack"
	@echo "  make down          Stop the full stack"
	@echo "  make build         Build the app + Qdrant images without starting"
	@echo "  make logs          Tail logs from the running stack"
	@echo "  make ps            Show status of the running stack"
	@echo "  make seed          Seed the catalog (DB + Qdrant) - run after 'make up'/'make up-build'"
	@echo ""
	@echo "  Dev tooling (local, via uv):"
	@echo "  make install       Install dependencies (uv sync)"
	@echo "  make test          Run the test suite"
	@echo "  make lint          Lint app/scripts/tests with ruff"
	@echo "  make fmt           Format app/scripts/tests with ruff"
	@echo "  make clean         Remove caches and local DB files"

install:
	uv sync

build:
	docker compose build

up:
	docker compose up -d
	@echo "App:    http://localhost:8000"
	@echo "Qdrant: http://localhost:6333/dashboard"

up-build:
	docker compose up -d --build
	@echo "App:    http://localhost:8000"
	@echo "Qdrant: http://localhost:6333/dashboard"

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

seed:
	docker compose exec app uv run --no-sync python scripts/seed_catalog.py

test:
	uv run pytest -v

lint:
	uv run ruff check app scripts tests

fmt:
	uv run ruff format app scripts tests

clean:
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
	rm -f smartreco.db
