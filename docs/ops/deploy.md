# Deployment Guide

Self-hosted deployment on a Linux server with Nginx, Postgres, Redis, and systemd (or Docker Compose). Works identically for local dev and prod — the only difference is `backend/.env`.

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose (runs Postgres, Redis, GlitchTip)
- Nginx (production only — for TLS termination)

---

## Fresh deploy — 5 steps

```bash
# 1. Clone
git clone https://github.com/youruser/atlas-insight.git
cd atlas-insight

# 2. Configure
cp backend/.env.example backend/.env
# Edit backend/.env — see "Environment variables" below

# 3. Bootstrap (venv + npm + postgres + migrate)
make init

# 4. Start full stack
make start

# 5. Create GlitchTip admin + promote Atlas user
make glitchtip-create-admin EMAIL=you@example.com PASSWORD=yourpassword
make promote-user EMAIL=you@example.com
```

`make start` handles service ordering automatically:
- Starts Postgres + Redis
- Starts GlitchTip, waits for health, provisions org/projects, writes `SENTRY_DSN` to `backend/.env`
- Starts Django, Celery worker, Celery beat, Flower, Vite (dev) or serves static build (prod)
- Starts Cloudflare tunnel if `CLOUDFLARE_TUNNEL_TOKEN` is set

**Production shortcut** — interactive script handles steps 1–5, systemd services, and nginx:

```bash
make production-release
```

---

## Environment variables

```bash
cp backend/.env.example backend/.env
```

**Change for production** (dev defaults are fine locally):

| Variable | Dev default | Prod value |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | `config.settings.production` |
| `SECRET_KEY` | insecure placeholder | long random string |
| `DEBUG` | `True` | `False` (or omit — prod settings force it) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | your domain(s) |
| `SECURE_SSL_REDIRECT` | `False` | `False` (keep False — nginx handles TLS) |

**Required in production** (missing vars crash on startup):

| Variable | Description |
|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(50))"` |
| `POSTGRES_DB` / `USER` / `PASSWORD` / `HOST` / `PORT` | Postgres connection |
| `REDIS_URL` | `redis://localhost:6379/1` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `GITHUB_WEBHOOK_SECRET` | Secret for GitHub push webhooks |
| `FIELD_ENCRYPTION_KEY` | Fernet key for PAT storage (see below) |

**Generate keys:**
```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(50))"

# FIELD_ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# GITHUB_WEBHOOK_SECRET
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Optional but recommended:**

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | Server-level token — raises GitHub rate limit to 5000/hr |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth for Atlas login |
| `FRONTEND_URL` | Public URL of frontend (e.g. `https://yoursite.com`) |
| `BACKEND_URL` | Public URL of API (e.g. `https://api.yoursite.com`) |
| `CORS_ALLOWED_ORIGINS` | Frontend origin(s) |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins |
| `CLOUDFLARE_TUNNEL_TOKEN` | Enables Cloudflare tunnel on `make start` |
| `FEATURED_REPO_URL` | GitHub URL of a public repo to feature on the home page |

**GlitchTip variables:**

| Variable | Description |
|---|---|
| `GLITCHTIP_SECRET_KEY` | Strong random string for GlitchTip (required in prod) |
| `GLITCHTIP_DOMAIN` | Public GlitchTip URL (e.g. `https://glitch.yoursite.com`) |
| `GLITCHTIP_CSRF_TRUSTED_ORIGINS` | **Must include every scheme+host users access GlitchTip from.** Missing entries cause 403 on login. Example: `https://glitch.yoursite.com,http://localhost:4505` |
| `SENTRY_DSN` | Written automatically by `make start` — do not edit manually |

> **`SECURE_SSL_REDIRECT` must stay `False`** when running behind nginx or Cloudflare. Both terminate TLS and forward HTTP to Django. Setting it `True` causes an infinite redirect loop.

---

## GitHub OAuth app (optional — for private repo access)

1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2. Homepage URL: your Atlas frontend URL
3. Authorization callback URL: `https://api.yoursite.com/accounts/github/login/callback/`
4. Copy Client ID and Secret into `.env` as `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`
5. In Django admin → Sites → change domain to your production domain
6. In Django admin → Social Applications → add GitHub with your credentials

---

## Production release (automated)

```bash
make production-release
```

Interactive script — walks through the full deployment:

1. Prompts for install path, domains, admin email, GlitchTip password, service user
2. Generates `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `GITHUB_WEBHOOK_SECRET`, `GLITCHTIP_SECRET_KEY`
3. Runs `make init` (venv + npm + postgres + migrate)
4. Starts GlitchTip and creates admin user
5. Starts full stack
6. **Confirms paths before writing** systemd service files to `/etc/systemd/system/`
7. `systemctl enable --now` the services
8. Prints nginx config and offers to write + enable it

Re-run safely — each step asks before acting.

---

## Updating a production instance

```bash
make prod-update
```

Pulls latest code, re-installs deps, runs migrations, rebuilds frontend, then restarts services via `systemctl` (or `make restart` if not running under systemd).

Manual equivalent:

```bash
git pull
cd backend && .venv/bin/pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py collectstatic --no-input
cd ../frontend && npm ci && npm run build
systemctl restart atlas-django atlas-celery atlas-celery-beat
```

---

## Systemd service units

### Django (Gunicorn)

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

### Celery worker

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
Environment=ATLAS_SERVICE=celery-workers
ExecStart=/opt/atlas-insight/backend/.venv/bin/celery \
    -A config worker \
    --loglevel=info \
    --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
```

### Celery beat

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
Environment=ATLAS_SERVICE=celery-beat
ExecStart=/opt/atlas-insight/backend/.venv/bin/celery \
    -A config beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always

[Install]
WantedBy=multi-user.target
```

### Flower (optional)

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
Environment=ATLAS_SERVICE=celery-flower
ExecStart=/opt/atlas-insight/backend/.venv/bin/celery \
    -A config flower \
    --port=4504
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now atlas-django atlas-celery atlas-celery-beat
```

---

## Nginx configuration

```nginx
# /etc/nginx/sites-available/atlas-insight

# API
server {
    listen 443 ssl;
    server_name api.yoursite.com;

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

# Frontend
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

## GlitchTip operations

```bash
make start-glitchtip       # start + provision org/projects + write SENTRY_DSN
make setup-glitchtip       # re-run provisioning + refresh DSN (idempotent)
make glitchtip-verify      # show projects + service tag inventory
make sentry-test-services  # emit test logs to all service buckets
make logs-glitchtip        # tail GlitchTip container logs

make glitchtip-db-dump     # backup → _running/backups/
make reset-glitchtip       # drop + recreate GlitchTip DB, re-provision
make fresh-glitchtip       # dump, then reset
```

**Service tags** — all Django sub-apps route to the `Backend` project, distinguished by `service` tag:

| Service tag | What it covers |
|---|---|
| `django` | Django web process |
| `django-api` | `apps.api` |
| `django-analysis` | `apps.analysis` |
| `django-repositories` | `apps.repositories` |
| `django-users` | `apps.users` |
| `django-config` | `config.*` modules |
| `celery-workers` | Celery worker |
| `celery-beat` | Celery beat scheduler |
| `celery-flower` | Flower |

Filter in GlitchTip Issues/Logs: add tag filter `service = django-analysis` etc.

---

## Startup / shutdown order

`make start` and `make stop` handle ordering automatically.

Manual order if needed:
1. Start Postgres + Redis
2. Start GlitchTip (`glitchtip-web` + `glitchtip-worker`)
3. Start Django / Celery / Beat / Flower / Vite

Shutdown is reverse order — stop GlitchTip last so app shutdown logs are captured.

---

## Disk management

Cloned repos are cached in `_running/repo_cache/`. On busy instances this grows large.

| Variable | Default | Description |
|---|---|---|
| `EVICT_AFTER_DAYS` | `30` | Delete clones not accessed in N days |
| `RUNS_TO_KEEP_PER_REPO` | `10` | Trim old analysis result rows per repo |
