# Atlas Insight

[![Atlas Insight](https://atlas.dsyndicate.dev/api/v1/repositories/badge/LunarVagabond/Atlas-Insight.svg)](https://atlas.dsyndicate.dev/r/LunarVagabond/Atlas-Insight)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-42b883.svg)](https://vuejs.org/)
[![Django](https://img.shields.io/badge/Django-5-092e20.svg)](https://www.djangoproject.com/)

**Repository archaeology and static analysis platform.**

Paste a GitHub repository URL and get deep architecture insights, commit history analysis, dependency health reports, security findings, OSS readiness scoring, and contributor guidance.

Atlas Insight performs deterministic repository analysis entirely within the application and can optionally generate structured context for use with external AI tools.

> Atlas Insight does **not** send repository contents to AI providers. Optional export features generate structured context that users may manually provide to external AI tools.

Analysis results are archived. Re-running a repository first checks for new commits and reuses existing results when nothing has changed.

---

**Quick Links:** [Features](#features) • [Quick Start](#quick-start) • [API](#api-reference) • [Deployment](#deployment) • [Contributing](#contributing)

---

<p align="center">
  <img src="docs/image_assets/dashboard.png" alt="Atlas Insight Dashboard" width="48%" />
  <img src="docs/image_assets/architecture.png" alt="Architecture View" width="48%" />
</p>

<p align="center">
  <img src="docs/image_assets/repo_health.png" alt="Repository Health View" width="48%" />
  <img src="docs/image_assets/heuristics.png" alt="Heuristics View" width="48%" />
</p>

---

## Features

| Feature                   | What you get                                                               |
| ------------------------- | -------------------------------------------------------------------------- |
| **Commit analysis**       | Velocity trends, contributor churn, burnout signals, activity decay        |
| **Architecture analysis** | Import graphs, circular dependencies, god modules, hot files               |
| **Dependency health**     | Dependency inventory, lockfile checks, Docker image warnings               |
| **Security scanning**     | Secret detection, `.gitignore` hygiene, repository safety signals          |
| **Heuristic scoring**     | Eleven repository risk and maintenance indicators                          |
| **OSS Score**             | Open-source readiness assessment from 0–10                                 |
| **Contributing path**     | Actionable contribution opportunities from issues and repository structure |
| **Architecture tours**    | Guided exploration paths through major subsystems                          |
| **Health badges**         | Embeddable SVG badges for analyzed repositories                            |

---

## OSS Score

OSS Score is a heuristic assessment of how approachable and maintainable a repository is for open-source contributors.

The score incorporates signals such as:

* Documentation quality
* Contributor friendliness
* Repository activity
* CI/CD maturity
* Dependency health
* Security hygiene
* Project structure
* Contributor distribution and bus factor
* Maintenance indicators
* Open issue management
* Development practices

OSS Score is intended as a directional indicator rather than an objective measure of software quality. A lower score may highlight maintenance or contribution risks rather than deficiencies in the software itself.

---

## Stack

| Layer       | Technology                        |
| ----------- | --------------------------------- |
| Backend API | Django 5 + Django Ninja           |
| Task Queue  | Celery + Redis                    |
| Database    | PostgreSQL 17                     |
| Frontend    | Vue 3 + TypeScript + Vite + Pinia |

**Default Ports**

| Service         | Port |
| --------------- | ---- |
| Django API      | 4500 |
| Vite Dev Server | 4501 |
| Redis           | 4502 |
| PostgreSQL      | 4503 |
| Flower          | 4504 |

---

## Quick Start

```bash
cp backend/.env.example backend/.env

# Optional but recommended:
# Add a GITHUB_TOKEN for higher GitHub API rate limits

make setup
docker compose up -d

make -C backend migrate
make start
```

### Local Services

| Service      | URL                            |
| ------------ | ------------------------------ |
| Frontend     | http://localhost:4501          |
| API          | http://localhost:4500          |
| OpenAPI Docs | http://localhost:4500/api/docs |
| Flower       | http://localhost:4504          |

---

## Development

### Process Management

```bash
make start
make stop
make restart
make status
make logs
```

### Backend

```bash
cd backend

# Run management commands
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/python manage.py <command>

# Run tests
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest

# Run a specific test file
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest apps/repositories/tests/test_models.py

# Linting
.venv/bin/ruff check .

# Formatting
.venv/bin/black .
```

### Frontend

```bash
cd frontend

# Type checking
node_modules/.bin/vue-tsc --noEmit

# Production build
make build
```

---

## API Reference

Interactive OpenAPI documentation is available at:

```text
/api/docs
```

when the application is running.

### Core Endpoints

| Method | Endpoint                                        | Description                          |
| ------ | ----------------------------------------------- | ------------------------------------ |
| POST   | `/api/v1/repositories/analyze`                  | Submit a repository for analysis     |
| GET    | `/api/v1/repositories/runs/{id}`                | Retrieve analysis status and results |
| GET    | `/api/v1/repositories/badge/{owner}/{name}.svg` | Generate repository health badge     |

### Just-In-Time Endpoints

These endpoints retrieve live data and cache responses in Redis for 15 minutes unless otherwise noted.

| Method | Endpoint                                                  | Description                   |
| ------ | --------------------------------------------------------- | ----------------------------- |
| GET    | `/api/v1/repositories/runs/{id}/issues`                   | Live GitHub issues            |
| GET    | `/api/v1/repositories/runs/{id}/prs`                      | Open pull requests            |
| GET    | `/api/v1/repositories/runs/{id}/diff`                     | Delta from previous analysis  |
| GET    | `/api/v1/repositories/runs/{id}/file-history?path=<path>` | Recent file history           |
| GET    | `/api/v1/repositories/runs/{id}/similar`                  | Similar repository profiles   |
| GET    | `/api/v1/repositories/runs/{id}/vulnerabilities`          | Dependency vulnerability data |
| GET    | `/api/v1/repositories/runs/{id}/constellation`            | Repository relationship graph |

---

## Deployment

Production deployment documentation is available at:

```text
docs/ops/deploy.md
```

The deployment guide includes:

* Nginx configuration
* systemd services
* Environment variables
* PostgreSQL setup
* Redis configuration
* Reverse proxy configuration
* Operational guidance

---

## Contributing

Contributions, bug reports, feature requests, and architectural discussions are welcome.

If you're looking for a place to start, Atlas Insight surfaces contributor-friendly opportunities directly through its repository analysis workflow.

Please review:

* CONTRIBUTING.md
* SECURITY.md
* CODE_OF_CONDUCT.md

before submitting pull requests.

---

## License

Released under the MIT License.

See [LICENSE](LICENSE) for details.

---

_If Atlas Insight has been useful to you and you'd like to support ongoing development, consider buying me a coffee._

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/lunarvagabond)