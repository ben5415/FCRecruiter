SHELL := /bin/bash

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
BACKEND_APP := app.main:app

.PHONY: help setup setup-db migrate tenant create-multitenant-db install install-backend install-frontend \
	dev dev-backend dev-frontend test test-backend build build-frontend

help:
	@echo "Available commands:"
	@echo "  make setup          Create .venv and install Python/npm dependencies"
	@echo "  make setup-db       Enable required PostgreSQL extensions"
	@echo "  make migrate        Apply database schema migrations"
	@echo "  make tenant ARGS='list'  Manage tenants through the server-side CLI"
	@echo "  make create-multitenant-db  Clone the current DB and apply tenant migration"
	@echo "  make dev-backend    Start FastAPI on http://localhost:8000"
	@echo "  make dev-frontend   Start React on http://localhost:5173"
	@echo "  make test           Run backend tests"
	@echo "  make build          Build the frontend"

setup: install-backend install-frontend

# Alias for setup, kept for discoverability.
install: setup

$(PYTHON):
	python3 -m venv $(VENV)

install-backend: $(PYTHON)
	$(PIP) install -r requirements.txt

install-frontend:
	npm install --prefix frontend

setup-db:
	$(PYTHON) scripts/enable_unaccent.py
	$(MAKE) migrate

migrate:
	PYTHONPATH=backend $(PYTHON) -m alembic upgrade head

tenant:
	PYTHONPATH=backend $(PYTHON) scripts/manage_tenants.py $(ARGS)

create-multitenant-db:
	PYTHONPATH=backend $(PYTHON) scripts/create_multitenant_database.py

# Run both development servers. Ctrl+C stops the Make target and its children.
dev:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) dev-backend & \
	$(MAKE) dev-frontend & \
	wait

dev-backend:
	PYTHONPATH=backend $(PYTHON) -m uvicorn $(BACKEND_APP) --reload --port 8000

dev-frontend:
	npm run dev --prefix frontend

test: test-backend

test-backend:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=backend $(PYTHON) -m pytest backend/tests -q

build: build-frontend

build-frontend:
	npm run build --prefix frontend
