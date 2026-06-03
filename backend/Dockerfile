# Build context: repo root (so .git is accessible for contributor stats)
# docker compose uses: context: .. / dockerfile: backend/Dockerfile

# Stage 1: Python deps
FROM python:3.11-slim AS deps
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Generate contributor stats from live git history
# This stage has access to .git so we can bake the stats into the image.
FROM python:3.11-slim AS git-stats
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /repo
COPY .git .git
COPY backend/contributors backend/contributors
COPY backend/scripts/build_contributor_stats.py backend/scripts/build_contributor_stats.py
RUN python backend/scripts/build_contributor_stats.py \
      --output backend/contributors_stats.json

# Stage 3: Final image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY backend/ .
COPY --from=git-stats /repo/backend/contributors_stats.json ./contributors_stats.json
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:4500", "--workers", "4", "--timeout", "120"]
