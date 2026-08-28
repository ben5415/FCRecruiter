SHELL := /bin/bash

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
BACKEND_APP := app.main:app
AGENT_APP := agent_service.app.main:app

.PHONY: help setup setup-db migrate tenant create-multitenant-db install install-backend install-agent install-frontend \
	dev dev-backend dev-agent dev-frontend test test-backend test-agent build build-frontend

help:
	@echo "Available commands:"
	@echo "  make setup          Create .venv and install Python/npm dependencies"
	@echo "  make setup-db       Enable required PostgreSQL extensions"
	@echo "  make migrate        Apply database schema migrations"
	@echo "  make tenant ARGS='list'  Manage tenants through the server-side CLI"
	@echo "  make create-multitenant-db  Clone the current DB and apply tenant migration"
	@echo "  make dev-backend    Start FastAPI on http://localhost:8000"
	@echo "  make dev-agent      Start Agent Service on http://localhost:8001"
	@echo "  make dev-frontend   Start React on http://localhost:5173"
	@echo "  make test           Run backend and Agent Service tests"
	@echo "  make build          Build the frontend"

setup: install-backend install-agent install-frontend

# Alias for setup, kept for discoverability.
install: setup

$(PYTHON):
	python3 -m venv $(VENV)

install-backend: $(PYTHON)
	$(PIP) install -r requirements.txt

install-agent: $(PYTHON)
	$(PIP) install -r agent_service/requirements.txt

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

# Run all development servers. Ctrl+C stops the Make target and its children.
dev:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) dev-backend & \
	$(MAKE) dev-agent & \
	$(MAKE) dev-frontend & \
	wait

dev-backend:
	PYTHONPATH=backend $(PYTHON) -m uvicorn $(BACKEND_APP) --reload --port 8000

dev-agent:
	PYTHONPATH=. $(PYTHON) -m uvicorn $(AGENT_APP) --reload --port 8001

dev-frontend:
	npm run dev --prefix frontend

test: test-backend test-agent

test-backend:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=backend $(PYTHON) -m pytest backend/tests -q

test-agent:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. $(PYTHON) -m pytest agent_service/tests -q

build: build-frontend

build-frontend:
	npm run build --prefix frontend
