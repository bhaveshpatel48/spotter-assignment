.PHONY: install dev backend-dev frontend-dev up down test backend-test frontend-test \
	lint backend-lint frontend-lint format

# Load .env (if present) into every recipe's environment.
ifneq (,$(wildcard .env))
include .env
export
endif

UV := env -u VIRTUAL_ENV uv

install:
	cd backend && $(UV) sync
	cd frontend && npm install

# Backend on :8000 and frontend on :5173, side by side. Ctrl+C stops both.
dev:
	$(MAKE) -j2 backend-dev frontend-dev

backend-dev:
	cd backend && $(UV) run python manage.py runserver 8000

frontend-dev:
	cd frontend && npm run dev

# Production images via Docker: app on :8080, API on :8000.
up:
	docker compose up --build

down:
	docker compose down

test: backend-test frontend-test

backend-test:
	cd backend && DJANGO_SECRET_KEY=test-only-secret-key $(UV) run pytest

frontend-test:
	cd frontend && npm test

lint: backend-lint frontend-lint

backend-lint:
	cd backend && $(UV) run ruff check . && $(UV) run ruff format --check .

frontend-lint:
	cd frontend && npm run lint && npm run typecheck

format:
	cd backend && $(UV) run ruff format . && $(UV) run ruff check --fix .
