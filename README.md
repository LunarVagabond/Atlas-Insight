# Atlas Insight

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-42b883.svg)](https://vuejs.org/)
[![Django](https://img.shields.io/badge/Django-5-092e20.svg)](https://www.djangoproject.com/)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/lunarvagabond)

**Repository archaeology and static analysis platform.** Paste a GitHub URL and get deep architecture insights, commit history analysis, dependency health reports, and heuristic risk scores — deterministic in-app analysis, plus optional AI context export for tools outside Atlas Insight.

Analysis results are archived. Re-running a repo first checks for new commits; no work is done if nothing has changed.

---

## Features

| Feature | What you get |
|---|---|
| **Commit analysis** | Velocity trends, contributor churn, burnout signals, activity decay |
| **Architecture** | Import graph, god modules, circular dependencies, hot files |
| **Dependency health** | Declared deps, Docker base image warnings, missing lockfiles |
| **Security scan** | Accidentally committed secrets, `.gitignore` gaps |
| **Heuristic scores** | 11 risk signals: abandonment, monolith growth, CI health, bus factor, and more |
| **OSS Score** | 0–10 summary of open-source readiness |
| **Contributing path** | Actionable opportunities surfaced from GitHub issues + structural gaps |
| **Architecture tours** | Guided reading paths through subsystems |

---

## Stack

| Layer | Tech |
|---|---|
| Backend API | Django 5 + Django Ninja (type-safe, OpenAPI auto-docs) |
| Task queue | Celery + Redis |
| Database | PostgreSQL 17 |
| Frontend | Vue 3 + TypeScript + Vite + Pinia |

**Ports:** Django `4500` · Vite `4501` · Redis `4502` · Postgres `4503` · Flower `4504`

---

## Quick Start

```bash
cp backend/.env.example backend/.env   # add GITHUB_TOKEN for higher rate limits
make setup                             # creates .venv, npm install
docker compose up -d                   # postgres + redis
make -C backend migrate
make start
```

| Service | URL |
|---|---|
| Frontend | http://localhost:4501 |
| API | http://localhost:4500 |
| API docs (OpenAPI) | http://localhost:4500/api/docs |
| Flower (task monitor) | http://localhost:4504 |

---

## Development

### Process management

```bash
make start / stop / restart / status / logs
```

### Backend

```bash
cd backend

# Run a management command
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/python manage.py <cmd>

# Run tests
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest

# Run a single test file
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest apps/repositories/tests/test_models.py

# Lint / format
.venv/bin/ruff check .
.venv/bin/black .
```

### Frontend

```bash
# Type check
cd frontend && node_modules/.bin/vue-tsc --noEmit

# Production build
make -C frontend build
```

---

## API Reference

Full interactive docs at `/api/docs` when the server is running.

### Core endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/repositories/analyze` | Submit a GitHub URL for analysis |
| `GET` | `/api/v1/repositories/runs/{id}` | Poll run status and retrieve results |
| `GET` | `/api/v1/repositories/badge/{owner}/{name}.svg` | Embeddable health badge (SVG) |

### JIT (just-in-time) endpoints

These fetch live data on demand and are cached in Redis for 15 minutes unless noted.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/repositories/runs/{id}/issues` | Live GitHub issues |
| `GET` | `/api/v1/repositories/runs/{id}/prs` | Live open PRs with issue refs |
| `GET` | `/api/v1/repositories/runs/{id}/diff` | Delta vs previous run (no extra cache) |
| `GET` | `/api/v1/repositories/runs/{id}/file-history?path=<path>` | Last 10 commits for a file |
| `GET` | `/api/v1/repositories/runs/{id}/similar` | Runs with a similar heuristic profile |
| `GET` | `/api/v1/repositories/runs/{id}/vulnerabilities` | Dependency CVE data |
| `GET` | `/api/v1/repositories/runs/{id}/constellation` | Repo relationship graph data |

---

## Deployment

See [docs/ops/deploy.md](docs/ops/deploy.md) for the full production guide — Nginx config, systemd units, env vars, and database setup.
