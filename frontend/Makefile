SHELL := /bin/bash
MAKEFILE_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(realpath $(MAKEFILE_DIR)/..)
RUNNING_DIR := $(REPO_ROOT)/_running

VITE := $(MAKEFILE_DIR)node_modules/.bin/vite

.PHONY: setup start stop restart status build type-check logs

setup:
	@echo "Installing frontend dependencies..."
	@cd $(MAKEFILE_DIR) && npm install
	@echo "Frontend setup complete."

start: _ensure_running_dirs
	@echo "Starting Vite dev server (port 4501)..."
	@cd $(MAKEFILE_DIR) && $(VITE) \
	  > $(RUNNING_DIR)/logs/vite.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/vite.pid
	@echo "Frontend running at http://localhost:4501"

stop:
	@PID_FILE=$(RUNNING_DIR)/pids/vite.pid; \
	if [ -f "$$PID_FILE" ]; then \
	  PID=$$(cat "$$PID_FILE"); \
	  echo "Stopping Vite (PID $$PID)..."; \
	  kill "$$PID" 2>/dev/null || true; \
	  rm -f "$$PID_FILE"; \
	else \
	  echo "Vite not running."; \
	fi

restart: stop start

status:
	@PID_FILE=$(RUNNING_DIR)/pids/vite.pid; \
	if [ -f "$$PID_FILE" ]; then \
	  PID=$$(cat "$$PID_FILE"); \
	  if kill -0 "$$PID" 2>/dev/null; then \
	    echo "  vite: running (PID $$PID)"; \
	  else \
	    echo "  vite: dead (stale PID $$PID)"; \
	    rm -f "$$PID_FILE"; \
	  fi; \
	else \
	  echo "  vite: stopped"; \
	fi

build:
	@cd $(MAKEFILE_DIR) && npm run build

type-check:
	@cd $(MAKEFILE_DIR) && node_modules/.bin/vue-tsc --noEmit

logs:
	@tail -f $(RUNNING_DIR)/logs/vite.log

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
