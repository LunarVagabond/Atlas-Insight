SHELL := /bin/bash
MAKEFILE_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
REPO_ROOT := $(realpath $(MAKEFILE_DIR)/..)
RUNNING_DIR := $(REPO_ROOT)/_running

VENV := $(MAKEFILE_DIR).venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
CELERY := $(VENV)/bin/celery

DJANGO_ENV := DJANGO_SETTINGS_MODULE=config.settings.development

.PHONY: setup start stop restart status migrate shell logs

setup:
	@echo "Creating Python virtual environment..."
	@python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip --quiet
	@$(PIP) install -r requirements-dev.txt --quiet
	@echo "Backend setup complete."

start: _ensure_running_dirs
	@echo "Starting Django (port 4500)..."
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py runserver 0.0.0.0:4500 --noreload \
	  >> $(RUNNING_DIR)/logs/django.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/django.pid
	@echo "Starting Celery worker..."
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(CELERY) -A config worker -l info \
	  >> $(RUNNING_DIR)/logs/celery.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/celery.pid
	@echo "Starting Flower (port 4504)..."
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(CELERY) -A config flower --port=4504 \
	  >> $(RUNNING_DIR)/logs/flower.log 2>&1 & echo $$! > $(RUNNING_DIR)/pids/flower.pid

stop:
	@for svc in django celery flower; do \
	  PID_FILE=$(RUNNING_DIR)/pids/$$svc.pid; \
	  if [ -f "$$PID_FILE" ]; then \
	    PID=$$(cat "$$PID_FILE"); \
	    echo "Stopping $$svc (PID $$PID)..."; \
	    kill "$$PID" 2>/dev/null || true; \
	    rm -f "$$PID_FILE"; \
	  fi; \
	done

restart: stop start

migrate:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py migrate

shell:
	@cd $(MAKEFILE_DIR) && $(DJANGO_ENV) $(PYTHON) manage.py shell

status:
	@for svc in django celery flower; do \
	  PID_FILE=$(RUNNING_DIR)/pids/$$svc.pid; \
	  if [ -f "$$PID_FILE" ]; then \
	    PID=$$(cat "$$PID_FILE"); \
	    if kill -0 "$$PID" 2>/dev/null; then \
	      echo "  $$svc: running (PID $$PID)"; \
	    else \
	      echo "  $$svc: dead (stale PID $$PID)"; \
	      rm -f "$$PID_FILE"; \
	    fi; \
	  else \
	    echo "  $$svc: stopped"; \
	  fi; \
	done

logs:
	@tail -f \
	  $(RUNNING_DIR)/logs/django.log \
	  $(RUNNING_DIR)/logs/celery.log \
	  $(RUNNING_DIR)/logs/flower.log

_ensure_running_dirs:
	@mkdir -p $(RUNNING_DIR)/logs $(RUNNING_DIR)/pids
