# Development Setup

Stack: Django 5 + Django Ninja · Celery + Redis · PostgreSQL 17 · Vue 3 + TypeScript + Vite

Port layout: Django `4500` · Vite `4501` · Redis `4502` · Postgres `4503` · Flower `4504`

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose (runs Postgres and Redis)

---

## First-time setup

```bash
cp backend/.env.example backend/.env   # edit secrets — add GITHUB_TOKEN for higher rate limits
make setup                             # creates .venv, runs npm install
docker compose up -d                   # start postgres + redis
make -C backend migrate
make start
```

App: `http://localhost:4501` · API: `http://localhost:4500` · API docs: `http://localhost:4500/api/docs`

---

## Daily workflow

```bash
make start      # start full stack
make stop       # stop everything
make restart    # restart full stack
make status     # show what's running
make logs       # tail all logs
```

---

## Backend

Always use the project `.venv` — never the system Python.

```bash
cd backend

# Run a management command
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/python manage.py <cmd>

# Django shell
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/python manage.py shell

# Run all tests
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest

# Run a specific test file
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest apps/repositories/tests/test_models.py

# Linting / formatting
.venv/bin/ruff check .
.venv/bin/black .
```

### Adding a new API endpoint

Each feature area gets its own `Router` in `apps/<area>/router.py`, then registered in `config/urls.py`:

```python
# config/urls.py
api.add_router('/v1/<area>/', router)
```

The `NinjaAPI` instance lives in `config/urls.py`. Django Ninja generates OpenAPI docs automatically.

### Adding a Celery task

Tasks live in `apps/analysis/tasks.py` (or sub-modules). `autodiscover_tasks()` picks them up from all `INSTALLED_APPS` — no manual registration needed.

### Settings

Settings use `python-decouple` — values come from `backend/.env`. `LOG_DIR` is `REPO_ROOT/_running/logs/` and is created on startup.

---

## Frontend

```bash
cd frontend

# Type check
node_modules/.bin/vue-tsc --noEmit

# Production build
npm run build
```

### Style rules

- **Zero `<style>` blocks** in `.vue` files — all styles live in `src/styles/`
- Design tokens in `src/styles/_variables.scss`
- BEM naming: `.block__element--modifier`
- Add new partials to `src/styles/main.scss`

### State management

Pinia stores in `src/stores/`. Add feature stores as separate files, not one monolithic store.

---

## Project layout

```
backend/
  config/           Django project package
    settings/
      base.py       shared config (reads from env via python-decouple)
      development.py
      production.py
    celery.py       Celery app
    urls.py         mounts NinjaAPI at /api/; register routers here
  apps/
    repositories/   Repository + AnalysisRun models
    analysis/       Celery tasks for repo cloning and analysis
    api/            Django Ninja routers

frontend/src/
  styles/           all styles — no <style> blocks in .vue files
  components/       reusable components
  views/            route-level components
  router/index.ts   Vue Router (history mode)
  stores/index.ts   Pinia stores
```

---

## Teardown and rebuild

Full clean wipe:

```bash
make teardown           # stop everything, docker down -v, remove _running/.venv/node_modules
make init               # re-setup from scratch
make start
make glitchtip-create-admin EMAIL=you@example.com PASSWORD=yourpassword
make promote-user EMAIL=you@example.com
```
