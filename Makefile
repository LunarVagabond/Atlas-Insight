SHELL := /bin/bash
ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
RUNNING_DIR := $(ROOT_DIR)/_running

# Pass ARGS= through to sub-targets that support it
# e.g. make makemigrations ARGS=repositories
# e.g. make test ARGS=apps/repositories/tests/ -v

.PHONY: setup start stop restart status logs \
        migrate makemigrations createsuperuser shell dbshell collectstatic \
        test lint format \
        build type-check

# ── Stack lifecycle ────────────────────────────────────────────────────────────

setup:
	@$(MAKE) -C backend setup
	@$(MAKE) -C frontend setup

start: _ensure_running_dirs
	@echo "Starting Docker services..."
	@docker compose up -d
	@echo "Starting backend..."
	@$(MAKE) -C backend start
	@echo "Starting frontend..."
	@$(MAKE) -C frontend start
	@echo ""
	@echo "Atlas Insight running:"
	@echo "  API:    http://localhost:4500/api/v1/docs"
	@echo "  App:    http://localhost:4501"
	@echo "  Flower: http://localhost:4504"

stop:
	@$(MAKE) -C frontend stop || true
	@$(MAKE) -C backend stop || true
	@echo "Stopping Docker services..."
	@docker compose stop

restart: stop start

status:
	@echo "=== Docker ==="
	@docker compose ps
	@echo ""
	@echo "=== Backend ==="
	@$(MAKE) -C backend status --no-print-directory
	@echo ""
	@echo "=== Frontend ==="
	@$(MAKE) -C frontend status --no-print-directory

logs:
	@tail -f $(RUNNING_DIR)/logs/*.log

# ── Django management ──────────────────────────────────────────────────────────

migrate:
	@$(MAKE) -C backend migrate ARGS="$(ARGS)"

makemigrations:
	@$(MAKE) -C backend makemigrations ARGS="$(ARGS)"

createsuperuser:
	@$(MAKE) -C backend createsuperuser

shell:
	@$(MAKE) -C backend shell

dbshell:
	@$(MAKE) -C backend dbshell

collectstatic:
	@$(MAKE) -C backend collectstatic

# ── Testing & quality ──────────────────────────────────────────────────────────

test:
	@$(MAKE) -C backend test ARGS="$(ARGS)"

lint:
	@$(MAKE) -C backend lint

format:
	@$(MAKE) -C backend format

# ── Frontend ───────────────────────────────────────────────────────────────────

build:
	@$(MAKE) -C frontend build

type-check:
	@$(MAKE) -C frontend type-check

# ── Internal ───────────────────────────────────────────────────────────────────

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
