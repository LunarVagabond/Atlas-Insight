#!/usr/bin/env bash
# Atlas Insight — interactive production deployment script.
# Called by: make production-release
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Terminal helpers ──────────────────────────────────────────────────────────
BOLD='\033[1m'; BLUE='\033[0;34m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

banner() { echo -e "\n${BOLD}${BLUE}══ $1 ══${NC}"; }
ok()     { echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}!${NC} $1"; }
die()    { echo -e "  ${RED}✗${NC} $1" >&2; exit 1; }

ask() {
    # ask VARNAME "Prompt text" ["default"]
    local __var="$1" prompt="$2" default="${3:-}"
    if [[ -n "$default" ]]; then
        printf "${BOLD}%s${NC} [%s]: " "$prompt" "$default"
        read -r _val
        printf -v "$__var" '%s' "${_val:-$default}"
    else
        printf "${BOLD}%s${NC}: " "$prompt"
        read -r _val
        [[ -n "$_val" ]] || die "Value required for: $prompt"
        printf -v "$__var" '%s' "$_val"
    fi
}

ask_secret() {
    local __var="$1" prompt="$2"
    printf "${BOLD}%s${NC}: " "$prompt"
    read -rs _val; echo
    [[ ${#_val} -ge 8 ]] || die "Password must be 8+ characters."
    printf -v "$__var" '%s' "$_val"
}

confirm() {
    # confirm "Prompt" → returns 0 (yes) or 1 (no)
    printf "${BOLD}%s [Y/n]:${NC} " "${1:-Proceed?}"
    read -r _ans
    [[ -z "$_ans" || "$_ans" =~ ^[Yy]$ ]]
}

# ── Preflight ─────────────────────────────────────────────────────────────────

banner "Atlas Insight — Production Release"
echo "  Interactive deployment. Confirms before each major step."
echo "  Run from: $REPO_ROOT"

# Check basic requirements
command -v python3 >/dev/null || die "python3 not found"
command -v node    >/dev/null || die "node not found"
command -v docker  >/dev/null || die "docker not found"
command -v nginx   >/dev/null || warn "nginx not found — config will be written but not activated"
command -v systemctl >/dev/null || warn "systemctl not found — systemd step will be skipped"

# ── Gather configuration ──────────────────────────────────────────────────────

banner "Configuration"
echo "  Answer each prompt. Press Enter to accept the default shown in [ ]."
echo

ask  INSTALL_PATH    "Install path"                             "/opt/atlas-insight"
ask  BACKEND_DOMAIN  "Backend API domain  (e.g. api.example.com)"
ask  FRONTEND_DOMAIN "Frontend domain     (e.g. example.com)"
ask  GLITCH_DOMAIN   "GlitchTip domain    (e.g. glitch.example.com)"
ask  ADMIN_EMAIL     "Admin email"
ask_secret GLITCH_PW "GlitchTip admin password (8+ chars)"
ask  SVC_USER        "Run services as user"                     "www-data"
ask  POSTGRES_DB     "Postgres database name"                   "atlas_insight"
ask  POSTGRES_USER   "Postgres user"                            "atlas"
ask_secret POSTGRES_PW "Postgres password"
ask  POSTGRES_HOST   "Postgres host"                            "localhost"
ask  POSTGRES_PORT   "Postgres port"                            "5432"
ask  REDIS_URL       "Redis URL"                                "redis://localhost:6379/1"
ask  CELERY_URL      "Celery broker URL"                        "redis://localhost:6379/0"

echo
banner "Summary"
echo "  Install path:    $INSTALL_PATH"
echo "  Backend:         https://$BACKEND_DOMAIN"
echo "  Frontend:        https://$FRONTEND_DOMAIN"
echo "  GlitchTip:       https://$GLITCH_DOMAIN"
echo "  Admin email:     $ADMIN_EMAIL"
echo "  Service user:    $SVC_USER"
echo "  Postgres:        $POSTGRES_USER@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
echo "  Redis:           $REDIS_URL"
echo

confirm "Proceed with deployment?" || { echo "Aborted."; exit 0; }

# ── Step 1: Install path ──────────────────────────────────────────────────────

banner "Step 1 — Install path"
echo "  Source:      $REPO_ROOT"
echo "  Destination: $INSTALL_PATH"

if [[ "$REPO_ROOT" != "$INSTALL_PATH" ]]; then
    confirm "Copy repo to $INSTALL_PATH? (skips .git, _running, .venv, node_modules)" && {
        sudo mkdir -p "$INSTALL_PATH"
        sudo rsync -a \
            --exclude='.git' \
            --exclude='_running' \
            --exclude='backend/.venv' \
            --exclude='frontend/node_modules' \
            "$REPO_ROOT/" "$INSTALL_PATH/"
        sudo chown -R "$SVC_USER:$SVC_USER" "$INSTALL_PATH"
        ok "Copied to $INSTALL_PATH"
    }
else
    ok "Already at install path — no copy needed"
fi

cd "$INSTALL_PATH"

# ── Step 2: Configure .env ────────────────────────────────────────────────────

banner "Step 2 — Configure backend/.env"

ENV_FILE="$INSTALL_PATH/backend/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    cp "$INSTALL_PATH/backend/.env.example" "$ENV_FILE"
    ok "Created $ENV_FILE from example"
else
    ok "$ENV_FILE already exists — updating production values"
fi

# Generate secrets
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(50))")
WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
GLITCH_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(50))")

# Try cryptography for Fernet key; fall back to venv python after setup
if python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
    FIELD_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
else
    warn "cryptography not installed system-wide — FIELD_ENCRYPTION_KEY will be set after venv setup"
    FIELD_KEY="__GENERATE_AFTER_SETUP__"
fi

_sed() { sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE" 2>/dev/null || echo "$1=$2" >> "$ENV_FILE"; }

_sed DJANGO_SETTINGS_MODULE "config.settings.production"
_sed SECRET_KEY              "$SECRET_KEY"
_sed DEBUG                   "False"
_sed SECURE_SSL_REDIRECT     "False"
_sed ALLOWED_HOSTS           "$BACKEND_DOMAIN,localhost,127.0.0.1"
_sed POSTGRES_DB             "$POSTGRES_DB"
_sed POSTGRES_USER           "$POSTGRES_USER"
_sed POSTGRES_PASSWORD       "$POSTGRES_PW"
_sed POSTGRES_HOST           "$POSTGRES_HOST"
_sed POSTGRES_PORT           "$POSTGRES_PORT"
_sed REDIS_URL               "$REDIS_URL"
_sed CELERY_BROKER_URL       "$CELERY_URL"
_sed FRONTEND_URL            "https://$FRONTEND_DOMAIN"
_sed BACKEND_URL             "https://$BACKEND_DOMAIN"
_sed CORS_ALLOWED_ORIGINS    "https://$FRONTEND_DOMAIN"
_sed CSRF_TRUSTED_ORIGINS    "https://$BACKEND_DOMAIN,https://$FRONTEND_DOMAIN"
_sed GLITCHTIP_DOMAIN        "https://$GLITCH_DOMAIN"
_sed GLITCHTIP_SECRET_KEY    "$GLITCH_SECRET"
_sed GLITCHTIP_CSRF_TRUSTED_ORIGINS "https://$GLITCH_DOMAIN"
_sed GITHUB_WEBHOOK_SECRET   "$WEBHOOK_SECRET"
_sed FIELD_ENCRYPTION_KEY    "$FIELD_KEY"

ok "Environment configured"
echo "  Webhook secret: $WEBHOOK_SECRET  (add to GitHub repo → Settings → Webhooks)"
warn "Review $ENV_FILE — add GITHUB_TOKEN, GITHUB_CLIENT_ID/SECRET if needed"

# ── Step 3: Bootstrap ─────────────────────────────────────────────────────────

banner "Step 3 — Bootstrap (venv + npm + postgres + migrate)"
confirm "Run make init?" && {
    make -C "$INSTALL_PATH" init
    ok "Bootstrap complete"

    # Now generate FIELD_KEY with venv python if we couldn't earlier
    if [[ "$FIELD_KEY" == "__GENERATE_AFTER_SETUP__" ]]; then
        FIELD_KEY=$("$INSTALL_PATH/backend/.venv/bin/python" -c \
            "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        _sed FIELD_ENCRYPTION_KEY "$FIELD_KEY"
        ok "FIELD_ENCRYPTION_KEY generated"
    fi
}

# ── Step 4: GlitchTip ────────────────────────────────────────────────────────

banner "Step 4 — GlitchTip"
echo "  Will start GlitchTip and create admin: $ADMIN_EMAIL"
confirm "Start GlitchTip and create admin?" && {
    make -C "$INSTALL_PATH" start-glitchtip
    make -C "$INSTALL_PATH" glitchtip-create-admin \
        EMAIL="$ADMIN_EMAIL" PASSWORD="$GLITCH_PW"
    ok "GlitchTip ready — login at https://$GLITCH_DOMAIN"
}

# ── Step 5: Full stack ────────────────────────────────────────────────────────

banner "Step 5 — Start full stack"
confirm "Run make start + promote-user?" && {
    make -C "$INSTALL_PATH" start
    make -C "$INSTALL_PATH" promote-user EMAIL="$ADMIN_EMAIL"
    ok "Stack running"
}

# ── Step 6: Systemd services ──────────────────────────────────────────────────

banner "Step 6 — Systemd services"

if ! command -v systemctl >/dev/null; then
    warn "systemctl not available — skipping systemd setup"
else
    VENV="$INSTALL_PATH/backend/.venv"
    BACKEND_DIR="$INSTALL_PATH/backend"

    echo "  Service files: /etc/systemd/system/atlas-{django,celery,celery-beat,flower}.service"
    echo "  WorkingDirectory: $BACKEND_DIR"
    echo "  EnvironmentFile:  $ENV_FILE"
    echo "  Gunicorn/Celery:  $VENV/bin/{gunicorn,celery}"
    echo "  User:             $SVC_USER"
    echo

    confirm "Paths look correct? Write service files to /etc/systemd/system/?" && {

        sudo tee /etc/systemd/system/atlas-django.service > /dev/null <<SVCEOF
[Unit]
Description=Atlas Insight Django
After=network.target postgresql.service redis.service

[Service]
User=$SVC_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=$VENV/bin/gunicorn config.wsgi:application --bind 127.0.0.1:4500 --workers 4 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
SVCEOF

        sudo tee /etc/systemd/system/atlas-celery.service > /dev/null <<SVCEOF
[Unit]
Description=Atlas Insight Celery Worker
After=network.target redis.service

[Service]
User=$SVC_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
Environment=ATLAS_SERVICE=celery-workers
ExecStart=$VENV/bin/celery -A config worker --loglevel=info --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
SVCEOF

        sudo tee /etc/systemd/system/atlas-celery-beat.service > /dev/null <<SVCEOF
[Unit]
Description=Atlas Insight Celery Beat
After=network.target redis.service

[Service]
User=$SVC_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
Environment=ATLAS_SERVICE=celery-beat
ExecStart=$VENV/bin/celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always

[Install]
WantedBy=multi-user.target
SVCEOF

        sudo tee /etc/systemd/system/atlas-flower.service > /dev/null <<SVCEOF
[Unit]
Description=Atlas Insight Flower
After=network.target redis.service

[Service]
User=$SVC_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
Environment=ATLAS_SERVICE=celery-flower
ExecStart=$VENV/bin/celery -A config flower --port=4504
Restart=always

[Install]
WantedBy=multi-user.target
SVCEOF

        ok "Service files written"

        confirm "Enable and start atlas-django, atlas-celery, atlas-celery-beat?" && {
            sudo systemctl daemon-reload
            sudo systemctl enable --now atlas-django atlas-celery atlas-celery-beat
            ok "Services enabled and started"
            echo
            sudo systemctl status atlas-django atlas-celery atlas-celery-beat --no-pager -l 2>&1 | head -30
        }
    }
fi

# ── Step 7: Nginx ─────────────────────────────────────────────────────────────

banner "Step 7 — Nginx configuration"

NGINX_CONF_CONTENT="# Atlas Insight nginx config — generated by make production-release
server {
    listen 443 ssl;
    server_name $BACKEND_DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$BACKEND_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$BACKEND_DOMAIN/privkey.pem;

    client_max_body_size 10M;

    location /static/ {
        alias $INSTALL_PATH/backend/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:4500;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120;
    }
}

server {
    listen 443 ssl;
    server_name $FRONTEND_DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$FRONTEND_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$FRONTEND_DOMAIN/privkey.pem;

    root $INSTALL_PATH/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}

server {
    listen 80;
    server_name $BACKEND_DOMAIN $FRONTEND_DOMAIN $GLITCH_DOMAIN;
    return 301 https://\$host\$request_uri;
}"

echo "$NGINX_CONF_CONTENT"
echo

NGINX_TARGET="/etc/nginx/sites-available/atlas-insight"
confirm "Write this config to $NGINX_TARGET and enable it?" && {
    if command -v nginx >/dev/null; then
        echo "$NGINX_CONF_CONTENT" | sudo tee "$NGINX_TARGET" > /dev/null
        sudo ln -sf "$NGINX_TARGET" /etc/nginx/sites-enabled/atlas-insight 2>/dev/null || true
        sudo nginx -t && sudo systemctl reload nginx
        ok "Nginx configured and reloaded"
        warn "Ensure SSL certs exist at /etc/letsencrypt/live/$BACKEND_DOMAIN/ (use certbot)"
    else
        warn "nginx not found — writing config to $INSTALL_PATH/nginx-atlas-insight.conf instead"
        echo "$NGINX_CONF_CONTENT" > "$INSTALL_PATH/nginx-atlas-insight.conf"
        ok "Config written to $INSTALL_PATH/nginx-atlas-insight.conf — copy to nginx manually"
    fi
}

# ── Done ──────────────────────────────────────────────────────────────────────

banner "Deployment complete"
echo "  Frontend:   https://$FRONTEND_DOMAIN"
echo "  API docs:   https://$BACKEND_DOMAIN/api/docs"
echo "  GlitchTip:  https://$GLITCH_DOMAIN"
echo "  Flower:     https://$BACKEND_DOMAIN:4504  (or proxy separately)"
echo
echo "Next:"
echo "  • Issue SSL certs if not done: certbot --nginx -d $BACKEND_DOMAIN -d $FRONTEND_DOMAIN -d $GLITCH_DOMAIN"
echo "  • Add GITHUB_TOKEN to $ENV_FILE for higher API rate limits"
echo "  • Set up GitHub webhook: https://$BACKEND_DOMAIN/api/v1/repositories/webhooks/github"
echo "  • Verify GlitchTip: make glitchtip-verify"
echo "  • Future updates: make prod-update"
