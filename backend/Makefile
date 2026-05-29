MAKEFLAGS    += --no-print-directory
SHELL        := /bin/bash
MAKEFILE_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT    := $(realpath $(MAKEFILE_DIR)/..)
RUNNING_DIR  := $(REPO_ROOT)/_running

VENV    := $(MAKEFILE_DIR).venv
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
CELERY  := $(VENV)/bin/celery

DJANGO_ENV := DJANGO_SETTINGS_MODULE=config.settings.development

.PHONY: setup start stop restart status \
        start-django stop-django \
        start-celery stop-celery \
        start-flower stop-flower \
        migrate makemigrations createsuperuser shell dbshell collectstatic \
        test lint format logs \
        _ensure_running_dirs _start_svc _stop_svc

# ── Setup ──────────────────────────────────────────────────────────────────────

setup:
	@echo "Creating Python virtual environment..."
	@python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip --quiet
	@$(PIP) install -r requirements-dev.txt --quiet
	@echo "Backend setup complete."

# ── Stack lifecycle ────────────────────────────────────────────────────────────

start: _ensure_running_dirs start-django start-celery start-flower

stop: stop-django stop-celery stop-flower
	@for port in 4500 4504; do \
	  for pid in $$(ss -tlnp "sport = :$$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u); do \
	    echo "  Killing stale process on port $$port (PID $$pid)..."; \
	    kill "$$pid" 2>/dev/null || true; \
	  done; \
	done

restart: stop start

# ── Individual services ────────────────────────────────────────────────────────

start-django: _ensure_running_dirs
	@echo "Starting Django (port 4500)..."
	@PID_FILE=$(RUNNING_DIR)/pids/django.pid; \
	if [ -f "$$PID_FILE" ] && kill -0 "$$(cat $$PID_FILE)" 2>/dev/null; then \
	  echo "  django already running (PID $$(cat $$PID_FILE)), skipping"; \
	else \
	  rm -f "$$PID_FILE"; \
	  (cd $(MAKEFILE_DIR) && exec env $(DJANGO_ENV) $(PYTHON) manage.py runserver 0.0.0.0:4500 --noreload) \
	    > $(RUNNING_DIR)/logs/django.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/django.pid; \
	fi

stop-django:
	@PID_FILE=$(RUNNING_DIR)/pids/django.pid; \
	if [ -f "$$PID_FILE" ]; then \
	  PID=$$(cat "$$PID_FILE"); \
	  echo "Stopping django..."; \
	  PGID=$$(ps -o pgid= $$PID 2>/dev/null | tr -d ' '); \
	  if [ -n "$$PGID" ] && [ "$$PGID" != "0" ]; then \
	    kill -TERM -$$PGID 2>/dev/null || true; \
	  fi; \
	  kill $$PID 2>/dev/null || true; \
	  rm -f "$$PID_FILE"; \
	else \
	  echo "  django not running"; \
	fi; \
	for pid in $$(ss -tlnp "sport = :4500" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u); do \
	  kill "$$pid" 2>/dev/null || true; \
	done

start-celery: _ensure_running_dirs
	@echo "Starting Celery worker..."
	@PID_FILE=$(RUNNING_DIR)/pids/celery.pid; \
	if [ -f "$$PID_FILE" ] && kill -0 "$$(cat $$PID_FILE)" 2>/dev/null; then \
	  echo "  celery already running (PID $$(cat $$PID_FILE)), skipping"; \
	else \
	  rm -f "$$PID_FILE"; \
	  cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(CELERY) -A config worker -l info -n worker@%h \
	    > $(RUNNING_DIR)/logs/celery.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/celery.pid; \
	fi

stop-celery:
	@PID_FILE=$(RUNNING_DIR)/pids/celery.pid; \
	if [ -f "$$PID_FILE" ]; then \
	  PID=$$(cat "$$PID_FILE"); \
	  echo "Stopping celery (PID $$PID)..."; \
	  PGID=$$(ps -o pgid= $$PID 2>/dev/null | tr -d ' '); \
	  if [ -n "$$PGID" ] && [ "$$PGID" != "0" ]; then \
	    kill -TERM -$$PGID 2>/dev/null || kill $$PID 2>/dev/null || true; \
	  else \
	    kill $$PID 2>/dev/null || true; \
	  fi; \
	  rm -f "$$PID_FILE"; \
	else \
	  echo "  celery not running"; \
	fi

start-flower: _ensure_running_dirs
	@echo "Starting Flower (port 4504)..."
	@PID_FILE=$(RUNNING_DIR)/pids/flower.pid; \
	if [ -f "$$PID_FILE" ] && kill -0 "$$(cat $$PID_FILE)" 2>/dev/null; then \
	  echo "  flower already running (PID $$(cat $$PID_FILE)), skipping"; \
	else \
	  rm -f "$$PID_FILE"; \
	  sleep 2; \
	  (cd $(MAKEFILE_DIR) && exec env $(DJANGO_ENV) $(CELERY) -A config flower --port=4504) \
	    > $(RUNNING_DIR)/logs/flower.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/flower.pid; \
	fi

stop-flower:
	@PID_FILE=$(RUNNING_DIR)/pids/flower.pid; \
	if [ -f "$$PID_FILE" ]; then \
	  PID=$$(cat "$$PID_FILE"); \
	  echo "Stopping flower..."; \
	  PGID=$$(ps -o pgid= $$PID 2>/dev/null | tr -d ' '); \
	  if [ -n "$$PGID" ] && [ "$$PGID" != "0" ]; then \
	    kill -TERM -$$PGID 2>/dev/null || true; \
	  fi; \
	  kill $$PID 2>/dev/null || true; \
	  rm -f "$$PID_FILE"; \
	else \
	  echo "  flower not running"; \
	fi; \
	for pid in $$(ss -tlnp "sport = :4504" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u); do \
	  kill "$$pid" 2>/dev/null || true; \
	done

# ── Django management ──────────────────────────────────────────────────────────

migrate:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py migrate $(ARGS)

makemigrations:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py makemigrations $(ARGS)

createsuperuser:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py createsuperuser

shell:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py shell

dbshell:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py dbshell

collectstatic:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py collectstatic --noinput

# ── Testing & quality ──────────────────────────────────────────────────────────

test:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(VENV)/bin/pytest $(ARGS)

lint:
	@cd $(MAKEFILE_DIR) && $(VENV)/bin/ruff check .

format:
	@cd $(MAKEFILE_DIR) && $(VENV)/bin/black .

# ── Status & logs ─────────────────────────────────────────────────────────────

status:
	@for svc in django celery flower; do \
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

logs:
	@tail -f \
	  $(RUNNING_DIR)/logs/django.log \
	  $(RUNNING_DIR)/logs/celery.log \
	  $(RUNNING_DIR)/logs/flower.log

logs-django:
	@tail -f $(RUNNING_DIR)/logs/django.log 2>/dev/null || echo "No django log — is Django running? (make start-django)"

logs-celery:
	@tail -f $(RUNNING_DIR)/logs/celery.log 2>/dev/null || echo "No celery log — is Celery running? (make start-celery)"

logs-flower:
	@tail -f $(RUNNING_DIR)/logs/flower.log 2>/dev/null || echo "No flower log — is Flower running? (make start-flower)"

# ── Internal ───────────────────────────────────────────────────────────────────

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
