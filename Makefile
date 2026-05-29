MAKEFLAGS   += --no-print-directory
SHELL       := /bin/bash
ROOT_DIR    := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
RUNNING_DIR := $(ROOT_DIR)/_running
COMPOSE     := docker compose -f $(ROOT_DIR)/docker-compose.yml

# Read CLOUDFLARE_TUNNEL_TOKEN from backend/.env if not already set in environment
CLOUDFLARE_TUNNEL_TOKEN ?= $(shell grep '^CLOUDFLARE_TUNNEL_TOKEN=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')

.PHONY: help setup start stop restart status logs \
        start-django  stop-django \
        start-celery  stop-celery \
        start-flower  stop-flower \
        start-vite    stop-vite \
        start-postgres stop-postgres \
        start-redis    stop-redis \
        start-tunnel  stop-tunnel \
        migrate makemigrations createsuperuser shell dbshell collectstatic \
        test lint format build type-check \
        logs-django logs-celery logs-flower logs-vite \
        _ensure_running_dirs

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Atlas Insight — available targets"
	@echo ""
	@echo "  ── Full stack ───────────────────────────────────────────────────────"
	@echo "    start              Start everything (Docker + Django + Celery + Flower + Vite)"
	@echo "    stop               Stop everything"
	@echo "    restart            stop then start"
	@echo "    status             Full stack status"
	@echo "    logs               Tail all logs"
	@echo ""
	@echo "  ── Individual services ──────────────────────────────────────────────"
	@echo "    start-django / stop-django      Django dev server  (port 4500)"
	@echo "    start-celery / stop-celery      Celery worker"
	@echo "    start-flower / stop-flower      Flower monitor     (port 4504)"
	@echo "    start-vite   / stop-vite        Vite dev server    (port 4501)"
	@echo "    start-postgres / stop-postgres  Postgres container (port 4503)"
	@echo "    start-redis    / stop-redis     Redis container    (port 4502)"
	@echo "    start-tunnel   / stop-tunnel    Cloudflare tunnel  (requires CLOUDFLARE_TUNNEL_TOKEN)"
	@echo ""
	@echo "  ── Django management ────────────────────────────────────────────────"
	@echo "    migrate            Run migrations  (ARGS=app_label)"
	@echo "    makemigrations     Make migrations (ARGS=app_label)"
	@echo "    createsuperuser"
	@echo "    shell              Django shell"
	@echo "    dbshell            Postgres shell"
	@echo "    collectstatic"
	@echo ""
	@echo "  ── Quality ──────────────────────────────────────────────────────────"
	@echo "    test               Run pytest  (ARGS=path or -k filter)"
	@echo "    lint               Ruff check"
	@echo "    format             Black format"
	@echo "    type-check         vue-tsc"
	@echo "    build              Vite production build"
	@echo ""
	@echo "  ── Logs ─────────────────────────────────────────────────────────────"
	@echo "    logs               Tail all logs"
	@echo "    logs-django / logs-celery / logs-flower / logs-vite"
	@echo ""
	@echo "  ── First time ───────────────────────────────────────────────────────"
	@echo "    make setup && make start && make migrate"
	@echo ""

# ── Full stack ─────────────────────────────────────────────────────────────────

setup:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend setup
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend setup


start: _ensure_running_dirs
	@> $(RUNNING_DIR)/logs/django.log
	@> $(RUNNING_DIR)/logs/celery.log
	@> $(RUNNING_DIR)/logs/flower.log
	@> $(RUNNING_DIR)/logs/vite.log
	@$(COMPOSE) up -d --quiet-pull 2>&1 | grep -v "^$$"
	@echo "Waiting for Postgres..."
	@until $(COMPOSE) exec -T postgres pg_isready -q 2>/dev/null; do sleep 1; done
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend start
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend start
	@$(MAKE) --no-print-directory start-tunnel
	@echo ""
	@echo "Atlas Insight running:"
	@echo "  API:    http://localhost:4500/api/v1/docs"
	@echo "  App:    http://localhost:4501"
	@echo "  Flower: http://localhost:4504"
	@if [ -n "$(CLOUDFLARE_TUNNEL_TOKEN)" ]; then \
	  echo ""; \
	  echo "  Tunnel:"; \
	  echo "    App:    https://atlas.dsyndicate.dev"; \
	  echo "    API:    https://ai-api.dsyndicate.dev"; \
	  echo "    Flower: https://ai-flower.dsyndicate.dev"; \
	fi

stop:
	@$(MAKE) --no-print-directory stop-tunnel
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend stop
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend stop
	@$(COMPOSE) stop 2>&1 | grep -v "^$$"

restart: stop start

# ── Status ────────────────────────────────────────────────────────────────────

status:
	@echo ""
	@echo "━━━ Docker ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(COMPOSE) ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "━━━ Processes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@for svc in django celery flower vite; do \
	  PID_FILE=$(RUNNING_DIR)/pids/$$svc.pid; \
	  if [ -f "$$PID_FILE" ]; then \
	    PID=$$(cat "$$PID_FILE"); \
	    if kill -0 "$$PID" 2>/dev/null; then \
	      printf "  %-10s running  (PID $$PID)\n" "$$svc:"; \
	    else \
	      printf "  %-10s DEAD     (stale PID $$PID)\n" "$$svc:"; \
	      rm -f "$$PID_FILE"; \
	    fi; \
	  else \
	    printf "  %-10s stopped\n" "$$svc:"; \
	  fi; \
	done
	@echo ""
	@echo "━━━ Tunnel ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if docker inspect cloudflared >/dev/null 2>&1; then \
	  STATUS=$$(docker inspect --format='{{.State.Status}}' cloudflared 2>/dev/null); \
	  printf "  %-14s %s\n" "cloudflared:" "$$STATUS"; \
	else \
	  printf "  %-14s %s\n" "cloudflared:" "not running"; \
	fi
	@echo ""
	@echo "━━━ URLs ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@printf "  %-14s %s\n" "Django API:"  "http://localhost:4500/api/v1/docs"
	@printf "  %-14s %s\n" "Vite app:"    "http://localhost:4501"
	@printf "  %-14s %s\n" "Flower:"      "http://localhost:4504"
	@printf "  %-14s %s\n" "Redis:"       "localhost:4502"
	@printf "  %-14s %s\n" "Postgres:"    "localhost:4503"
	@if docker inspect cloudflared >/dev/null 2>&1 && [ "$$(docker inspect --format='{{.State.Status}}' cloudflared 2>/dev/null)" = "running" ]; then \
	  echo ""; \
	  printf "  %-14s %s\n" "App tunnel:"    "https://atlas.dsyndicate.dev"; \
	  printf "  %-14s %s\n" "API tunnel:"    "https://ai-api.dsyndicate.dev"; \
	  printf "  %-14s %s\n" "Flower tunnel:" "https://ai-flower.dsyndicate.dev"; \
	fi
	@echo ""

# ── Individual services ────────────────────────────────────────────────────────

start-django:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend start-django

stop-django:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend stop-django

start-celery:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend start-celery

stop-celery:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend stop-celery

start-flower:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend start-flower

stop-flower:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend stop-flower

start-vite:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend start-vite

stop-vite:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend stop-vite

start-postgres:
	@$(COMPOSE) start postgres

stop-postgres:
	@$(COMPOSE) stop postgres

start-redis:
	@$(COMPOSE) start redis

stop-redis:
	@$(COMPOSE) stop redis

start-tunnel:
	@if [ -z "$(CLOUDFLARE_TUNNEL_TOKEN)" ]; then \
	  echo "  tunnel:    skipped (CLOUDFLARE_TUNNEL_TOKEN not set)"; \
	else \
	  echo "Starting Cloudflare tunnel..."; \
	  docker stop cloudflared 2>/dev/null || true; \
	  docker rm cloudflared 2>/dev/null || true; \
	  CLOUDFLARE_TUNNEL_TOKEN=$(CLOUDFLARE_TUNNEL_TOKEN) $(COMPOSE) --profile tunnel up -d cloudflared 2>&1 | grep -v "^$$"; \
	fi

stop-tunnel:
	@docker stop cloudflared 2>/dev/null || true
	@docker rm cloudflared 2>/dev/null || true

# ── Django management ──────────────────────────────────────────────────────────

migrate:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend migrate ARGS="$(ARGS)"

makemigrations:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend makemigrations ARGS="$(ARGS)"

createsuperuser:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend createsuperuser

shell:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend shell

dbshell:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend dbshell

collectstatic:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend collectstatic

# ── Testing & quality ──────────────────────────────────────────────────────────

test:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend test ARGS="$(ARGS)"

lint:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend lint

format:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend format

build:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend build

type-check:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend type-check

# ── Logs ───────────────────────────────────────────────────────────────────────

logs:
	@tail -f $(RUNNING_DIR)/logs/*.log

logs-django:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-django

logs-celery:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-celery

logs-flower:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-flower

logs-vite:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend logs-vite

# ── Internal ───────────────────────────────────────────────────────────────────

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
