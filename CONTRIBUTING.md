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
<issue_number>-<short-description>   e.g. 42-fix-auth-token
noissue-<short-description>          e.g. noissue-update-readme
```

## Commit messages

```
[#<issue>] - <short description>
```

Examples:
```
[#42] - fix auth token expiry check
[#101] - add submodule champion detection
[noissue] - update readme typo
```

Use `[noissue]` when no issue exists.

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

## Pull requests

**Title format:** `<type>(<scope>): <short description>` — mirrors the commit convention used in this repo.

| Type | When to use |
|------|-------------|
| `feat` | New user-facing feature |
| `fix` | Bug fix |
| `refactor` | Internal restructure with no behavior change |
| `test` | Tests only |
| `docs` | Documentation only |
| `chore` | Build, config, dependency bumps |

Examples:
```
feat(analysis): add submodule champion detection
fix(frontend): correct pagination offset on home page
docs(contributing): add PR conventions section
```

**PR description should answer:**
- **What** — one-line summary of the change
- **Why** — motivation or linked issue (`Closes #123`)
- **Test plan** — what you ran to verify it works

Keep PRs focused. A PR that adds a feature and refactors an unrelated module is harder to review. Split when in doubt.

## Code style

- **Backend**: Black + Ruff. No comments unless the WHY is non-obvious.
- **Frontend**: Vue 3 + TypeScript. All styles in `src/styles/` — zero `<style>` blocks in `.vue` files. BEM naming.

## AI-assisted contributions

AI-assisted code is welcome. If any part of a commit was written or significantly shaped by an AI tool, add a trailer identifying it:

```bash
git commit -m "[#42] - add submodule detection" --trailer "AI-tool: Claude"
git commit -m "[#7] - correct pagination offset" --trailer "AI-tool: GitHub Copilot"
git commit -m "[noissue] - simplify router registration" --trailer "AI-tool: Cursor"
```

The trailer key is `AI-tool` — use whatever value names the tool. This lets us grep AI-assisted commits later:

```bash
git log --grep="AI-tool"
```

No judgment on AI use. The same quality bar applies: tests pass, linters clean, PR description explains what and why.

## Reporting bugs

Open a GitHub issue using the bug report template.

## Questions

Open a GitHub discussion or email lvagabond@dsyndicate.dev.
