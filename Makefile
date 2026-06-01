MAKEFLAGS   += --no-print-directory
SHELL       := /bin/bash
ROOT_DIR    := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
RUNNING_DIR := $(ROOT_DIR)/_running
COMPOSE     := docker compose -f $(ROOT_DIR)/docker-compose.yml --env-file $(ROOT_DIR)/backend/.env

# Read secrets from backend/.env if not already set in environment
CLOUDFLARE_TUNNEL_TOKEN ?= $(shell grep '^CLOUDFLARE_TUNNEL_TOKEN=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
GLITCHTIP_GITHUB_CLIENT_ID ?= $(shell grep '^GLITCHTIP_GITHUB_CLIENT_ID=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
GLITCHTIP_GITHUB_SECRET ?= $(shell grep '^GLITCHTIP_GITHUB_SECRET=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
POSTGRES_USER_VAL ?= $(shell grep '^POSTGRES_USER=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
GLITCHTIP_DOMAIN_VAL ?= $(shell grep '^GLITCHTIP_DOMAIN=' $(ROOT_DIR)/backend/.env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
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
		start-glitchtip stop-glitchtip logs-glitchtip configure-glitchtip setup-glitchtip glitchtip-db-dump reset-glitchtip fresh-glitchtip \
	glitchtip-create-admin sentry-test-services glitchtip-verify \
        migrate makemigrations createsuperuser shell dbshell collectstatic \
        test lint format build type-check \
		logs-django logs-celery logs-beat logs-flower logs-vite \
        _ensure_running_dirs

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Atlas Insight — available targets"
	@echo ""
	@echo "  ── Full stack ───────────────────────────────────────────────────────"
	@echo "    start              Start everything (Docker + GlitchTip + Django + Celery + Beat + Flower + Vite)"
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
	@echo "    start-glitchtip / stop-glitchtip  GlitchTip error tracking (port 4505)  (also runs in start/stop)"
	@echo "    logs-glitchtip                    Tail GlitchTip logs"
	@echo "    setup-glitchtip                   Bootstrap org/projects + refresh DSN"
	@echo "    glitchtip-create-admin            Create GlitchTip admin (EMAIL=... PASSWORD=...)"
	@echo "    glitchtip-db-dump                 Dump GlitchTip DB to _running/backups/"
	@echo "    reset-glitchtip                   Drop/recreate GlitchTip DB, then bootstrap"
	@echo "    fresh-glitchtip                   Dump DB, then reset from scratch"
	@echo "    sentry-test-services              Emit service-tagged test logs"
	@echo "    glitchtip-verify                  Show projects + Backend log service buckets"
	@echo "    promote-user                      Promote a Django user to superuser (EMAIL=... optional)"
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
	@echo "  ── First time / fresh deploy ────────────────────────────────────────"
	@echo "    1. cp backend/.env.example backend/.env  (fill in secrets)"
	@echo "    2. make init         (venv + npm + postgres + migrate)"
	@echo "    3. make start        (full stack)"
	@echo "    4. make promote-user EMAIL=you@example.com"
	@echo ""
	@echo "  ── Clean wipe (dev) ─────────────────────────────────────────────────"
	@echo "    make teardown        (stop + docker down -v + rm _running/.venv/node_modules)"
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
	@$(MAKE) --no-print-directory start-glitchtip
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend start
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend start
	@$(MAKE) --no-print-directory start-tunnel
	@echo ""
	@echo "Atlas Insight running:"
	@echo "  API:        http://localhost:4500/api/docs"
	@echo "  App:        http://localhost:4501"
	@echo "  Flower:     http://localhost:4504"
	@echo "  GlitchTip:  https://glitch.dsyndicate.dev"
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
	@$(MAKE) --no-print-directory stop-glitchtip
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
	@printf "  %-14s %s\n" "GlitchTip:"  "https://glitch.dsyndicate.dev  (run: make start-glitchtip)"
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

start-glitchtip:
	@echo "  Creating GlitchTip database if needed..."
	@docker exec github-archaeologist-postgres-1 psql -U "$(or $(POSTGRES_USER_VAL),atlas)" -d postgres \
		-c "CREATE DATABASE glitchtip" 2>&1 | grep -v "already exists" || true
	@$(COMPOSE) --profile glitchtip up -d glitchtip-migrate 2>&1 | grep -v "^$$"
	@$(COMPOSE) --profile glitchtip up -d glitchtip-web glitchtip-worker 2>&1 | grep -v "^$$"
	@echo "  Waiting for GlitchTip..."
	@until curl -sf http://localhost:4505/api/0/ > /dev/null 2>&1; do sleep 2; done
	@$(MAKE) --no-print-directory setup-glitchtip
	@echo "  GlitchTip UI: https://glitch.dsyndicate.dev"
	@echo "  First time? Run: make glitchtip-create-admin EMAIL=you@example.com PASSWORD=yourpassword"

setup-glitchtip:
	@docker cp $(ROOT_DIR)/scripts/glitchtip_setup.py github-archaeologist-glitchtip-web-1:/tmp/glitchtip_setup.py
	@_GT_DOMAIN="$(or $(GLITCHTIP_DOMAIN_VAL),https://glitch.dsyndicate.dev)"; \
	_GT_DSN=$$(docker exec \
		github-archaeologist-glitchtip-web-1 \
		python /tmp/glitchtip_setup.py "$$_GT_DOMAIN" 2>/dev/null | tail -1); \
	if echo "$$_GT_DSN" | grep -qE '^https?://[a-f0-9]+@'; then \
		sed -i "s|^SENTRY_DSN=.*|SENTRY_DSN=$$_GT_DSN|" $(ROOT_DIR)/backend/.env; \
		echo "  DSN written to backend/.env: $$_GT_DSN"; \
	else \
		echo "  Could not parse DSN output from glitchtip_setup.py"; \
	fi

configure-glitchtip:
	@_GT_DOMAIN="$(or $(GLITCHTIP_DOMAIN_VAL),https://glitch.dsyndicate.dev)"; \
	docker cp $(ROOT_DIR)/scripts/glitchtip_setup.py github-archaeologist-glitchtip-web-1:/tmp/glitchtip_setup.py; \
	_GT_DSN=$$(docker exec \
		github-archaeologist-glitchtip-web-1 \
		python /tmp/glitchtip_setup.py "$$_GT_DOMAIN" 2>/dev/null | tail -1); \
	if echo "$$_GT_DSN" | grep -qE '^https?://[a-f0-9]+@'; then \
		sed -i "s|^SENTRY_DSN=.*|SENTRY_DSN=$$_GT_DSN|" $(ROOT_DIR)/backend/.env; \
		echo "DSN: $$_GT_DSN"; \
	else \
		echo "No user found — sign in at $$_GT_DOMAIN first"; \
	fi

stop-glitchtip:
	@$(COMPOSE) --profile glitchtip stop glitchtip-web glitchtip-worker glitchtip-migrate 2>&1 | grep -v "^$$"

logs-glitchtip:
	@$(COMPOSE) --profile glitchtip logs -f glitchtip-web glitchtip-worker

glitchtip-db-dump:
	@mkdir -p $(RUNNING_DIR)/backups
	@OUT_FILE="$(RUNNING_DIR)/backups/glitchtip_$$(date -u +%Y%m%dT%H%M%SZ).sql"; \
	docker exec github-archaeologist-postgres-1 pg_dump -U "$(or $(POSTGRES_USER_VAL),atlas)" glitchtip > "$$OUT_FILE"; \
	echo "  GlitchTip DB dump written: $$OUT_FILE"

reset-glitchtip:
	@echo "Resetting GlitchTip database from scratch..."
	@$(MAKE) --no-print-directory stop-glitchtip
	@docker exec github-archaeologist-postgres-1 psql -U "$(or $(POSTGRES_USER_VAL),atlas)" -d postgres \
		-c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'glitchtip' AND pid <> pg_backend_pid();" > /dev/null
	@docker exec github-archaeologist-postgres-1 psql -U "$(or $(POSTGRES_USER_VAL),atlas)" -d postgres \
		-c "DROP DATABASE IF EXISTS glitchtip;" > /dev/null
	@docker exec github-archaeologist-postgres-1 psql -U "$(or $(POSTGRES_USER_VAL),atlas)" -d postgres \
		-c "CREATE DATABASE glitchtip;" > /dev/null
	@$(MAKE) --no-print-directory start-glitchtip

fresh-glitchtip:
	@$(MAKE) --no-print-directory glitchtip-db-dump
	@$(MAKE) --no-print-directory reset-glitchtip

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
	@echo "Local _running/logs files are disabled. Use make logs-glitchtip and GlitchTip UI logs."

logs-django:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-django

logs-celery:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-celery

logs-beat:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-beat

sentry-test-services:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend sentry-test-services

promote-user:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend promote-user EMAIL="$(EMAIL)" USERNAME="$(USERNAME)"

glitchtip-create-admin:
	@if [ -z "$(EMAIL)" ] || [ -z "$(PASSWORD)" ]; then \
	  echo "Usage: make glitchtip-create-admin EMAIL=you@example.com PASSWORD=yourpassword"; \
	  exit 1; \
	fi
	@docker exec \
	  -e DJANGO_SUPERUSER_EMAIL="$(EMAIL)" \
	  -e DJANGO_SUPERUSER_USERNAME="$(EMAIL)" \
	  -e DJANGO_SUPERUSER_PASSWORD="$(PASSWORD)" \
	  github-archaeologist-glitchtip-web-1 \
	  python manage.py createsuperuser --noinput 2>&1 | grep -v "already exists" || true
	@$(MAKE) --no-print-directory setup-glitchtip
	@echo "  GlitchTip admin ready: $(EMAIL)"

glitchtip-verify:
	@docker cp $(ROOT_DIR)/scripts/glitchtip_verify.py github-archaeologist-glitchtip-web-1:/tmp/glitchtip_verify.py
	@docker exec github-archaeologist-glitchtip-web-1 python /tmp/glitchtip_verify.py

logs-flower:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/backend logs-flower

logs-vite:
	@$(MAKE) --no-print-directory -C $(ROOT_DIR)/frontend logs-vite

# ── Internal ───────────────────────────────────────────────────────────────────

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
