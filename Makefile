.PHONY: install dev backend-dev test backend-test lint backend-lint format

# Load .env (if present) into every recipe's environment.
ifneq (,$(wildcard .env))
include .env
export
endif

UV := env -u VIRTUAL_ENV uv

install:
	cd backend && $(UV) sync

dev: backend-dev

backend-dev:
	cd backend && $(UV) run python manage.py runserver 8000

test: backend-test

backend-test:
	cd backend && DJANGO_SECRET_KEY=test-only-secret-key $(UV) run pytest

lint: backend-lint

backend-lint:
	cd backend && $(UV) run ruff check . && $(UV) run ruff format --check .

format:
	cd backend && $(UV) run ruff format . && $(UV) run ruff check --fix .
