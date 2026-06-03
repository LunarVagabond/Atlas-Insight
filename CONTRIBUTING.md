# Contributing to Atlas Insight

## Setup

```bash
cp backend/.env.example backend/.env   # edit secrets
make setup                             # creates .venv, npm install
docker compose up -d                   # postgres + redis
make -C backend migrate
make start
```

## Branch naming

```
<issue_number>-<short-description> (i.e. 1-update-website )
noissue-<short-description> (i.e. noissue-update-website)
```

## Making changes

1. Fork the repo and create a branch from `main`
2. Write tests for new code — see `backend/apps/*/tests/` for patterns
3. Run linters before opening a PR:

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/black .
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest
```

```bash
cd frontend
node_modules/.bin/vue-tsc --noEmit
npm test
```

4. Add an entry under `## Unreleased` in `CHANGELOG.md`
5. Open a pull request against `main`

## Code style

- **Backend**: Black + Ruff. No comments unless the WHY is non-obvious.
- **Frontend**: Vue 3 + TypeScript. All styles in `src/styles/` — zero `<style>` blocks in `.vue` files. BEM naming.

## Reporting bugs

Open a GitHub issue using the bug report template.

## Questions

Open a GitHub discussion or email lvagabond@dsyndicate.dev.
