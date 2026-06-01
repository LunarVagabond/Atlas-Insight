# Deployment Guide — Atlas Insight

Self-hosted deployment on a Linux server with Nginx, Postgres, Redis, and systemd (or Docker Compose).

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 17
- Redis 7+
- Nginx
- Docker + Docker Compose (required if running bundled GlitchTip stack)

---

## 1. Clone and install

```bash
git clone https://github.com/youruser/atlas-insight.git
cd atlas-insight

# Python virtualenv
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Frontend build
cd ../frontend
npm ci
npm run build
```

---

## 2. Environment variables

Copy and populate the env file:

```bash
cp backend/.env.example backend/.env
```

**Required in production** (missing vars will crash on startup):

| Variable | Description |
|---|---|
| `SECRET_KEY` | Long random string — `python -c "import secrets; print(secrets.token_hex(50))"` |
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_HOST` | Postgres host |
| `POSTGRES_PORT` | Postgres port (default 5432) |
| `REDIS_URL` | `redis://localhost:6379/1` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `GITHUB_WEBHOOK_SECRET` | Secret for GitHub push webhooks |
| `FIELD_ENCRYPTION_KEY` | Fernet key for PAT storage — see below |

**Optional but recommended:**

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | Server-level token — raises GitHub API rate limit to 5000/hr |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth app credentials |
| `FRONTEND_URL` | Public URL of your frontend (e.g. `https://yoursite.com`) |
| `BACKEND_URL` | Public URL of your API (e.g. `https://api.yoursite.com`) |
| `ALLOWED_HOSTS` | Comma-separated list of allowed Django hostnames |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origin(s) |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins |
| `FEATURED_REPO_URL` | GitHub URL of a public repo to feature on the home page |
| `SENTRY_DSN` | DSN used by backend services for error/log capture |
| `GLITCHTIP_GITHUB_CLIENT_ID` / `GLITCHTIP_GITHUB_SECRET` | GitHub OAuth app credentials for GlitchTip login |
| `GLITCHTIP_DOMAIN` | Public GlitchTip URL (e.g. `https://glitch.yoursite.com`) |
| `GLITCHTIP_PROJECTS` | Comma-separated GlitchTip projects to auto-provision |
| `GLITCHTIP_PRIMARY_PROJECT` | Project name whose DSN is written back to `SENTRY_DSN` |

**Generate the encryption key:**

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 3. Database setup

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py createsuperuser
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py collectstatic --no-input
```

---

## 4. GitHub OAuth app (optional — for private repo access)

1. Go to GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2. Set **Homepage URL** to your frontend URL
3. Set **Authorization callback URL** to `https://api.yoursite.com/accounts/github/login/callback/`
4. Copy Client ID and Client Secret into `.env`
5. In Django admin → Sites → change domain to your production domain
6. In Django admin → Social Applications → add GitHub with your credentials

---

## 4b. GlitchTip bootstrap (recommended)

Atlas Insight includes a built-in GlitchTip bootstrap flow for local/dev and Docker-based environments.

Commands:

```bash
make start-glitchtip
make setup-glitchtip
make glitchtip-db-dump
make reset-glitchtip
make fresh-glitchtip
```

`make setup-glitchtip` is idempotent and will:

- create/update organization `atlas-insight`
- create/update GitHub social login app for GlitchTip (when env vars are set)
- create/update configured projects
- write DSN for the primary project back into `backend/.env` as `SENTRY_DSN`

Default auto-provisioned projects:

- `Backend`
- `Frontend`

Recommended service model:

- Keep only `Backend` and `Frontend` projects.
- Use backend `service` tags (`django-api`, `django-analysis`, `celery-workers`, etc.) for granularity within `Backend`.

Reset + recovery flow:

```bash
# 1) save snapshot
make glitchtip-db-dump

# 2) destructive rebuild from empty database
make reset-glitchtip

# 3) one-command backup + rebuild
make fresh-glitchtip
```

Debug validation command:

```bash
make sentry-test-services
make glitchtip-verify
```

This emits service-tagged test logs and then prints the effective project/service state from GlitchTip's database.

---

## 5. GitHub webhook (optional — for auto-re-analysis on push)

1. In GitHub repo settings → Webhooks → Add webhook
2. Payload URL: `https://api.yoursite.com/api/v1/repositories/webhooks/github`
3. Content type: `application/json`
4. Secret: the value of `GITHUB_WEBHOOK_SECRET`
5. Events: **Just the push event**

---

## 6. Gunicorn (Django)

```ini
# /etc/systemd/system/atlas-django.service
[Unit]
Description=Atlas Insight Django
After=network.target postgresql.service redis.service

[Service]
User=www-data
WorkingDirectory=/opt/atlas-insight/backend
EnvironmentFile=/opt/atlas-insight/backend/.env
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=/opt/atlas-insight/backend/.venv/bin/gunicorn \
    config.wsgi:application \
    --bind 127.0.0.1:4500 \
    --workers 4 \
    --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 7. Celery worker + beat

```ini
# /etc/systemd/system/atlas-celery.service
[Unit]
Description=Atlas Insight Celery Worker
After=network.target redis.service

[Service]
User=www-data
WorkingDirectory=/opt/atlas-insight/backend
EnvironmentFile=/opt/atlas-insight/backend/.env
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=/opt/atlas-insight/backend/.venv/bin/celery \
    -A config worker \
    --loglevel=info \
    --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/atlas-celery-beat.service
[Unit]
Description=Atlas Insight Celery Beat
After=network.target redis.service

[Service]
User=www-data
WorkingDirectory=/opt/atlas-insight/backend
EnvironmentFile=/opt/atlas-insight/backend/.env
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=/opt/atlas-insight/backend/.venv/bin/celery \
    -A config beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now atlas-django atlas-celery atlas-celery-beat
```

Optional Flower service:

```ini
# /etc/systemd/system/atlas-flower.service
[Unit]
Description=Atlas Insight Flower
After=network.target redis.service

[Service]
User=www-data
WorkingDirectory=/opt/atlas-insight/backend
EnvironmentFile=/opt/atlas-insight/backend/.env
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=/opt/atlas-insight/backend/.venv/bin/celery \
    -A config flower \
    --port=4504
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl enable --now atlas-flower
```

---

## 8. Nginx

```nginx
# /etc/nginx/sites-available/atlas-insight
server {
    listen 443 ssl;
    server_name api.yoursite.com;

    # SSL certs (e.g. from certbot)
    ssl_certificate     /etc/letsencrypt/live/api.yoursite.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yoursite.com/privkey.pem;

    client_max_body_size 10M;

    location /static/ {
        alias /opt/atlas-insight/backend/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:4500;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
    }
}

server {
    listen 443 ssl;
    server_name yoursite.com;

    ssl_certificate     /etc/letsencrypt/live/yoursite.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yoursite.com/privkey.pem;

    root /opt/atlas-insight/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 9. Disk considerations

Cloned repos are cached in `_running/repo_cache/`. On busy instances this can grow large.

- `EVICT_AFTER_DAYS` (default 30) — deletes clones not accessed in N days
- `RUNS_TO_KEEP_PER_REPO` (default 10) — trims old analysis result rows

Monitor with `make -C backend shell` → Django admin → Admin stats panel.

---

## 10. Updates

```bash
git pull
cd backend && .venv/bin/pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py collectstatic --no-input
cd ../frontend && npm ci && npm run build
systemctl restart atlas-django atlas-celery atlas-celery-beat
```

---

## 11. Startup/Shutdown order (logging)

If GlitchTip is your sink for startup/shutdown logs, order matters.

Recommended order:

1. Start Postgres + Redis
2. Start GlitchTip (`glitchtip-web` + `glitchtip-worker`)
3. Start Django/Celery/Beat/Flower/Vite

Shutdown order:

1. Stop app services (Django/Celery/Beat/Flower/Vite)
2. Stop GlitchTip last

The project `Makefile` follows this ordering so app startup and close-out logs have the best chance of being ingested.
