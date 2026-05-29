MAKEFLAGS    += --no-print-directory
SHELL        := /bin/bash
MAKEFILE_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT    := $(realpath $(MAKEFILE_DIR)/..)
RUNNING_DIR  := $(REPO_ROOT)/_running

VITE := $(MAKEFILE_DIR)node_modules/.bin/vite

.PHONY: setup start stop restart status start-vite stop-vite build type-check logs logs-vite _ensure_running_dirs

# ── Setup ──────────────────────────────────────────────────────────────────────

setup:
	@echo "Installing frontend dependencies..."
	@cd $(MAKEFILE_DIR) && npm install
	@echo "Frontend setup complete."

# ── Stack lifecycle ────────────────────────────────────────────────────────────

start: start-vite

stop: stop-vite

restart: stop start

# ── Individual services ────────────────────────────────────────────────────────

start-vite: _ensure_running_dirs
	@echo "Starting Vite dev server (port 4501)..."
	@PID_FILE=$(RUNNING_DIR)/pids/vite.pid; \
	if [ -f "$$PID_FILE" ] && kill -0 "$$(cat $$PID_FILE)" 2>/dev/null; then \
	  echo "  vite already running (PID $$(cat $$PID_FILE)), skipping"; \
	else \
	  rm -f "$$PID_FILE"; \
	  cd $(MAKEFILE_DIR) && $(VITE) \
	    > $(RUNNING_DIR)/logs/vite.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/vite.pid; \
	  echo "  Frontend running at http://localhost:4501"; \
	fi

stop-vite:
	@PID_FILE=$(RUNNING_DIR)/pids/vite.pid; \
	if [ -f "$$PID_FILE" ]; then \
	  PID=$$(cat "$$PID_FILE"); \
	  echo "Stopping vite (PID $$PID)..."; \
	  kill "$$PID" 2>/dev/null || true; \
	  rm -f "$$PID_FILE"; \
	  for pid in $$(ss -tlnp "sport = :4501" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u); do \
	    kill "$$pid" 2>/dev/null || true; \
	  done; \
	else \
	  echo "  vite not running"; \
	fi

# ── Build & type check ─────────────────────────────────────────────────────────

build:
	@cd $(MAKEFILE_DIR) && npm run build

type-check:
	@cd $(MAKEFILE_DIR) && node_modules/.bin/vue-tsc --noEmit

# ── Status & logs ─────────────────────────────────────────────────────────────

status:
	@PID_FILE=$(RUNNING_DIR)/pids/vite.pid; \
	if [ -f "$$PID_FILE" ]; then \
	  PID=$$(cat "$$PID_FILE"); \
	  if kill -0 "$$PID" 2>/dev/null; then \
	    printf "  %-10s running  (PID $$PID)\n" "vite:"; \
	  else \
	    printf "  %-10s DEAD     (stale PID $$PID)\n" "vite:"; \
	    rm -f "$$PID_FILE"; \
	  fi; \
	else \
	  printf "  %-10s stopped\n" "vite:"; \
	fi

logs:
	@tail -f $(RUNNING_DIR)/logs/vite.log

logs-vite:
	@tail -f $(RUNNING_DIR)/logs/vite.log 2>/dev/null || echo "No vite log — is Vite running? (make start-vite)"

# ── Internal ───────────────────────────────────────────────────────────────────

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
