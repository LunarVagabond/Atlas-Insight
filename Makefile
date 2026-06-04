MAKEFLAGS   += --no-print-directory
SHELL       := /bin/bash
ROOT_DIR    := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
RUNNING_DIR := $(ROOT_DIR)/_running
COMPOSE     := docker compose -f $(ROOT_DIR)/docker-compose.yml --env-file $(ROOT_DIR)/backend/.env

# Read secrets from backend/.env if not already set in environment
CLOUDFLARE_TUNNEL_TOKEN ?= $(shell grep '^CLOUDFLARE_TUNNEL_TOKEN=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
POSTGRES_USER_VAL ?= $(shell grep '^POSTGRES_USER=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
COMPOSE_BARE := docker compose -f $(ROOT_DIR)/docker-compose.yml

.PHONY: help setup init teardown production-release prod-update start stop restart status logs \
        start-django  stop-django \
        start-celery  stop-celery \
	start-beat    stop-beat \
        start-flower  stop-flower \
        start-vite    stop-vite \
        start-postgres stop-postgres \
        start-redis    stop-redis \
        start-tunnel  stop-tunnel \
        migrate makemigrations createsuperuser shell dbshell collectstatic \
        test lint format build type-check \
		logs-django logs-celery logs-beat logs-flower logs-vite \
        docker-up docker-down docker-build release \
        submit-repos \
        _ensure_running_dirs

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Atlas Insight — available targets"
	@echo ""
	@echo "  ── Full stack ───────────────────────────────────────────────────────"
	@echo "    start              Start everything (Docker + Django + Celery + Beat + Flower + Vite)"
	@echo "    stop               Stop everything"
	@echo "    restart            stop then start"
	@echo "    status             Full stack status"
	@echo "    logs               Tail all logs"
	@echo ""
	@echo "  ── Individual services ──────────────────────────────────────────────"
	@echo "    start-django / stop-django      Django dev server  (port 4500)"
	@echo "    start-celery / stop-celery      Celery worker"
	@echo "    start-beat   / stop-beat        Celery beat scheduler"
	@echo "    start-flower / stop-flower      Flower monitor     (port 4504)"
	@echo "    start-vite   / stop-vite        Vite dev server    (port 4501)"
	@echo "    start-postgres / stop-postgres  Postgres container (port 4503)"
	@echo "    start-redis    / stop-redis     Redis container    (port 4502)"
	@echo "    start-tunnel   / stop-tunnel    Cloudflare tunnel  (requires CLOUDFLARE_TUNNEL_TOKEN)"
	@echo "    promote-user                    Promote a Django user to superuser (EMAIL=... optional)"
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
	@echo "  ── Batch submission ─────────────────────────────────────────────────"
	@echo "    submit-repos       POST each URL in FILE to the analyze API"
	@echo "                       FILE=repos.txt (default)  HOST=http://localhost:4500"
	@echo ""
	@echo "  ── Logs ─────────────────────────────────────────────────────────────"
	@echo "    logs               Tail all logs"
	@echo "    logs-django / logs-celery / logs-flower / logs-vite"
	@echo ""
	@echo "  ── First time / fresh deploy ────────────────────────────────────────"
	@echo "    1. cp backend/.env.example backend/.env  (fill in secrets)"
	@echo "    2. make init         (venv + npm + postgres + migrate)"
	@echo "    3. make start        (full stack)"
	@echo "    4. make promote-user EMAIL=you@example.com"
	@echo ""
	@echo "  ── Clean wipe (dev) ─────────────────────────────────────────────────"
	@echo "    make teardown        (stop + docker down -v + rm _running/.venv/node_modules)"
	@echo ""
	@echo "  ── Docker (containerised stack) ─────────────────────────────────────"
	@echo "    docker-build         Build backend + frontend images"
	@echo "    docker-up            Start full containerised stack (app profile)"
	@echo "    docker-down          Stop and remove app containers"
	@echo ""
	@echo "  ── Release ──────────────────────────────────────────────────────────"
	@echo "    release              Interactive: bump version, build + tag images, push to ghcr.io"
	@echo ""
	@echo "  ── Production ───────────────────────────────────────────────────────"
	@echo "    production-release   Interactive prod deploy: systemd + nginx + full stack"
	@echo "    prod-update          git pull + pip + migrate + build + restart services"
	@echo ""

# ── Full stack ─────────────────────────────────────────────────────────────────

setup:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend setup
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend setup

init: setup
	@echo "Starting Postgres and Redis..."
	@$(COMPOSE) up -d postgres redis 2>&1 | grep -v "^$$"
	@echo "Waiting for Postgres..."
	@until $(COMPOSE) exec -T postgres pg_isready -q 2>/dev/null; do sleep 1; done
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend migrate
	@echo ""
	@echo "Init complete. Next: make start && make promote-user EMAIL=you@example.com"

teardown:
	@$(MAKE) --no-print-directory stop || true
	@$(COMPOSE) down -v 2>&1 | grep -v "^$$"
	@rm -rf $(ROOT_DIR)/_running $(ROOT_DIR)/backend/.venv $(ROOT_DIR)/frontend/node_modules
	@echo ""
	@echo "Torn down. Next: make init && make start"

production-release:
	@bash $(ROOT_DIR)/scripts/production-release.sh

prod-update:
	@echo "Pulling latest code..."
	@git -C $(ROOT_DIR) pull
	@echo "Installing backend deps..."
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend setup
	@echo "Running migrations..."
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend migrate
	@echo "Collecting static files..."
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend collectstatic
	@echo "Building frontend..."
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend build
	@echo "Restarting services..."
	@if systemctl is-active --quiet atlas-django 2>/dev/null; then \
	  sudo systemctl restart atlas-django atlas-celery atlas-celery-beat; \
	  echo "  systemd services restarted"; \
	else \
	  $(MAKE) --no-print-directory restart; \
	fi
	@echo "Done."


start: _ensure_running_dirs
	@$(COMPOSE) up -d --quiet-pull 2>&1 | grep -v "^$$"
	@echo "Waiting for Postgres..."
	@until $(COMPOSE) exec -T postgres pg_isready -q 2>/dev/null; do sleep 1; done
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend start
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend start
	@$(MAKE) --no-print-directory start-tunnel
	@echo ""
	@echo "Atlas Insight running:"
	@echo "  API:        http://localhost:4500/api/docs"
	@echo "  App:        http://localhost:4501"
	@echo "  Flower:     http://localhost:4504"
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
	@for svc in django celery beat flower vite; do \
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
	@printf "  %-14s %s\n" "Django API:"  "http://localhost:4500/api/docs"
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

start-beat:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend start-beat

stop-beat:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend stop-beat

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
	@echo "Dev logs: _running/logs/<service>.log (truncated on each start)"
	@echo "  tail -f $(ROOT_DIR)/_running/logs/django.log"

logs-django:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-django

logs-celery:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-celery

logs-beat:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-beat

promote-user:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend promote-user EMAIL="$(EMAIL)" USERNAME="$(USERNAME)"

logs-flower:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-flower

logs-vite:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend logs-vite

# ── Docker (full containerised stack) ─────────────────────────────────────────
# profile: app  — backend, celery, celery-beat, flower, frontend (nginx)
# Uses backend/.env for secrets; compose overrides POSTGRES_HOST/REDIS_URL for container networking.

docker-build:
	@$(COMPOSE) --profile app build

docker-up: _ensure_running_dirs
	@$(COMPOSE) up -d postgres redis
	@echo "Waiting for Postgres..."
	@until $(COMPOSE) exec -T postgres pg_isready -q 2>/dev/null; do sleep 1; done
	@$(COMPOSE) --profile app up -d
	@echo ""
	@echo "Atlas Insight (Docker) running:"
	@echo "  App:    http://localhost:4501"
	@echo "  API:    http://localhost:4500/api/docs"
	@echo "  Flower: http://localhost:4504"

docker-down:
	@$(COMPOSE) --profile app down

# ── Release ────────────────────────────────────────────────────────────────────

release:
	@bash $(ROOT_DIR)/scripts/release.sh

# ── Batch submission ──────────────────────────────────────────────────────────

SUBMIT_FILE ?= $(ROOT_DIR)/repos.txt
SUBMIT_HOST ?= http://localhost:4500

submit-repos:
	@if [ ! -f "$(SUBMIT_FILE)" ]; then \
	  echo "File not found: $(SUBMIT_FILE)"; \
	  echo "Create it with one GitHub URL per line, then re-run."; \
	  echo "Override path with: make submit-repos FILE=/path/to/urls.txt"; \
	  exit 1; \
	fi
	@echo "Submitting repos from $(SUBMIT_FILE) → $(SUBMIT_HOST)/api/v1/repositories/analyze"
	@echo ""
	@while IFS= read -r url || [ -n "$$url" ]; do \
	  url=$$(echo "$$url" | tr -d '[:space:]'); \
	  [ -z "$$url" ] && continue; \
	  [[ "$$url" == \#* ]] && continue; \
	  printf "  %-60s " "$$url"; \
	  response=$$(curl -s -o /dev/null -w "%{http_code}" \
	    -X POST "$(SUBMIT_HOST)/api/v1/repositories/analyze" \
	    -H "Content-Type: application/json" \
	    -d "{\"url\": \"$$url\"}"); \
	  if [ "$$response" = "200" ]; then \
	    echo "queued"; \
	  else \
	    echo "HTTP $$response"; \
	  fi; \
	done < "$(SUBMIT_FILE)"
	@echo ""
	@echo "Done."

# ── Internal ───────────────────────────────────────────────────────────────────

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
