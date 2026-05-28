SHELL := /bin/bash
ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
RUNNING_DIR := $(ROOT_DIR)/_running

.PHONY: setup start stop restart status logs

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
	@echo "  API:    http://localhost:4500"
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

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
