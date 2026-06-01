# Atlas Insight

Repository archaeology and static analysis platform. Paste a GitHub URL and get architecture insights, commit history analysis, dependency reports, and heuristic health scores — no AI, just data.

## What it does

- **Commit analysis** — velocity trends, contributor churn, burnout signals, activity decay
- **Architecture** — import graph, god modules, circular dependencies, hot files
- **Dependency health** — declared deps, Docker base image warnings, missing lockfiles
- **Security scan** — accidentally committed secrets, gitignore gaps
- **Heuristic scores** — 11 risk signals: abandonment, monolith growth, CI health, bus factor, and more
- **OSS Score** — 0–10 summary of open-source readiness
- **Contributing path** — actionable opportunities from GitHub issues + structural gaps
- **Architecture tours** — guided reading paths through subsystems

Results are archived. Re-running a repo first checks for new commits; no work done if nothing changed.

## Stack

| Layer | Tech |
|---|---|
| Backend API | Django 5 + Django Ninja |
| Task queue | Celery + Redis |
| Database | PostgreSQL 17 |
| Frontend | Vue 3 + TypeScript + Vite |

## Quick start

```bash
cp backend/.env.example backend/.env   # add GITHUB_TOKEN for higher rate limits
make setup
docker compose up -d                   # postgres + redis
make -C backend migrate
make start
```

App runs at `http://localhost:4501`. API at `http://localhost:4500`. API docs at `http://localhost:4500/api/docs`.

## Development

```bash
make start / stop / restart / status / logs

# Django
cd backend
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/python manage.py <cmd>
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest

# Frontend
cd frontend && node_modules/.bin/vue-tsc --noEmit
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for the full production guide — Nginx config, systemd units, env vars, and database setup.

## API

OpenAPI docs available at `/api/docs` once the server is running.

Key endpoints:
- `POST /api/v1/repositories/analyze` — submit a URL for analysis
- `GET /api/v1/repositories/runs/{id}` — poll run status / get results
- `GET /api/v1/repositories/badge/{owner}/{name}.svg` — embeddable health badge
- `GET /api/v1/repositories/runs/{id}/issues` — live GitHub issues (JIT, 15min cache)
- `GET /api/v1/repositories/runs/{id}/prs` — live open PRs (JIT, 15min cache)
- `GET /api/v1/repositories/runs/{id}/diff` — delta vs previous run

## License

MIT
