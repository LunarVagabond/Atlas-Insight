#!/bin/sh
set -e

# Run migrations and static file collection only for the web service.
# Celery worker/beat/flower skip this — they share the same image but different CMD.
if [ "$1" = "gunicorn" ]; then
    python manage.py migrate --no-input
    python manage.py collectstatic --no-input --clear
fi

exec "$@"
