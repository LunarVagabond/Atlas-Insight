# API Reference

Base URL: `https://<your-domain>/api/v1/`

Interactive OpenAPI docs (full schema, try-it-out): `/api/docs`
Machine-readable OpenAPI JSON: `/api/openapi.json`

---

## Authentication

Most endpoints require a Bearer token:

```
Authorization: Bearer <your-token>
```

Generate tokens at **Settings → API Tokens** in the UI, or via `POST /auth/tokens`.

Public endpoints (badge SVG, read-only run status on public repos) do not require authentication.

---

## Endpoints

### Submit a repository for analysis

```
POST /repositories/analyze
```

Submits a GitHub repository URL for analysis. If the repository has been analyzed before and no new commits exist on the target branch, returns the cached result immediately. Otherwise enqueues a new analysis run.

**Request body:**

```json
{
  "url": "https://github.com/owner/repo",
  "branch": "feat/my-feature",
  "pat": "ghp_...",
  "webhook_url": "https://your-server.example.com/callback"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | yes | GitHub repository URL |
| `branch` | string | no | Branch to analyze. Omit (or pass `""`) for the default branch |
| `pat` | string | no | GitHub personal access token for private repos. Stored encrypted; only needed once per repo |
| `webhook_url` | string | no | `https` URL to POST to when analysis completes — see [webhooks.md](webhooks.md) |

**Response:**

```json
{
  "run_id": "01914a3c-...",
  "status": "pending",
  "cached": false
}
```

| Field | Type | Description |
|---|---|---|
| `run_id` | UUID | Use this to poll status or fetch results |
| `status` | string | `pending` or `completed` |
| `cached` | bool | `true` = existing result returned, no new analysis enqueued |

**Status codes:** `200 OK` · `422 Unprocessable Entity` (bad URL) · `429 Too Many Requests` (10/hour limit)

---

### Poll run status / get results

```
GET /repositories/runs/{run_id}
```

Returns the current state of a run. Poll until `status` is `completed` or `failed`.

**Response:**

```json
{
  "id": "01914a3c-...",
  "status": "completed",
  "progress_step": "",
  "triggered_at": "2025-06-01T12:00:00Z",
  "completed_at": "2025-06-01T12:01:45Z",
  "repo_url": "https://github.com/owner/repo",
  "repo_owner": "owner",
  "repo_name": "repo",
  "branch": "feat/my-feature",
  "is_stale": false,
  "is_private": false,
  "last_fetched_at": "2025-06-01T12:01:45Z",
  "auth_token_warning": "",
  "cooldown_until": null,
  "result": { ... }
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `pending` · `running` · `completed` · `failed` |
| `progress_step` | string | Current step during analysis: `cloning` · `parsing` · `heuristics` · `metadata` · `finalizing` |
| `branch` | string | Branch analyzed. Empty string = default branch |
| `result` | object \| null | Full analysis payload; `null` while pending/running |
| `cooldown_until` | ISO timestamp \| null | If set, retry blocked until this time |

**Status codes:** `200 OK` · `403 Forbidden` (private repo, insufficient access) · `404 Not Found`

---

### List branches for a repository

```
GET /repositories/runs/{run_id}/branches
```

Returns all remote branches for the repository plus which branches have been analyzed.

**Response:**

```json
{
  "branches": ["main", "develop", "feat/my-feature"],
  "scanned": ["main", "feat/my-feature"]
}
```

| Field | Type | Description |
|---|---|---|
| `branches` | string[] | All branches on the remote (fetched live via git ls-remote) |
| `scanned` | string[] | Branches that have at least one completed analysis run |

---

### Resolve latest run by owner/name

```
GET /repositories/by-slug/{owner}/{name}
```

Returns the latest completed run for a repository without needing a `run_id`. Useful for building permalinks.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `branch` | string | Optional branch name. Omit for default branch |

**Response:**

```json
{
  "run_id": "01914a3c-...",
  "status": "completed"
}
```

---

### Retry a run

```
POST /repositories/runs/{run_id}/retry
```

Force re-analysis of a repository. Superusers bypass the 4-hour cooldown; regular users are rate-limited.

**Response:** same schema as `POST /repositories/analyze`

**Status codes:** `200 OK` · `429 Too Many Requests` (cooldown active) · `403 Forbidden`

---

### Run history timeline

```
GET /repositories/runs/{run_id}/timeline
```

Returns commit frequency and dependency count data for charting.

**Response:**

```json
{
  "commit_frequency": [{"week": "2025-01-01", "count": 12}, ...],
  "monthly_frequency": [...],
  "contributor_churn": [...],
  "dependency_count": 142
}
```

---

### JIT data endpoints

Fetch live GitHub data on-demand. Responses cached in Redis for 15 minutes unless noted.

#### Open issues

```
GET /repositories/runs/{run_id}/issues
```

#### Open pull requests

```
GET /repositories/runs/{run_id}/prs
```

#### Delta vs previous run

```
GET /repositories/runs/{run_id}/diff
```

Changes in heuristic scores, dependency counts, and structural metrics since the previous run. Not Redis-cached (uses DB).

#### File commit history

```
GET /repositories/runs/{run_id}/file-history?path=<path>
```

Last 10 commits that touched `<path>`. Cached 15 minutes.

#### Similar repositories

```
GET /repositories/runs/{run_id}/similar
```

Runs with a similar heuristic profile.

#### Dependency vulnerabilities

```
GET /repositories/runs/{run_id}/vulnerabilities
```

CVE data for detected dependencies.

#### PR impact analysis

```
GET /repositories/runs/{run_id}/pr-impact?pr=<number>
```

Impact analysis for a specific pull request number.

---

### Health badge

```
GET /repositories/badge/{owner}/{name}.svg
```

SVG badge showing the current OSS Score. No authentication required.

```markdown
![Atlas Insight Score](https://<your-domain>/api/v1/repositories/badge/torvalds/linux.svg)
```

---

### List runs

```
GET /repositories/runs/
```

**Query parameters:**

| Parameter | Default | Description |
|---|---|---|
| `q` | `""` | Filter by URL, owner, or repo name |
| `sort` | `triggered_at` | Sort field: `triggered_at` · `completed_at` · `status` |
| `order` | `desc` | `asc` or `desc` |
| `page` | `1` | Page number |
| `per_page` | `25` | Max 25 |
| `mine` | `false` | Authenticated users only: return only their runs |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "repo_id": "uuid",
      "status": "completed",
      "triggered_at": "2025-06-01T12:00:00Z",
      "completed_at": "2025-06-01T12:01:45Z",
      "repo_url": "https://github.com/owner/repo",
      "repo_owner": "owner",
      "repo_name": "repo",
      "is_stale": false,
      "is_private": false,
      "is_favorited": false,
      "last_fetched_at": "...",
      "tags": ["typescript", "library"],
      "has_previous_run": true,
      "primary_language": "TypeScript",
      "scanned_branch_count": 2,
      "cached_branch_count": 5
    }
  ],
  "total": 47,
  "page": 1,
  "per_page": 25
}
```

---

### Delete a run

```
DELETE /repositories/runs/{run_id}
```

Deletes a run for a private repository. Only the run's owner may delete it. If it's the last run for the repository, the repository record is also deleted.

**Status codes:** `204 No Content` · `403 Forbidden` · `404 Not Found`

---

## Auth endpoints

### Current user

```
GET /auth/me
```

**Response:**

```json
{
  "id": 1,
  "username": "octocat",
  "email": "octocat@github.com"
}
```

### API tokens

```
GET  /auth/tokens          # list active tokens
POST /auth/tokens          # create token  { "name": "CI pipeline" }
DELETE /auth/tokens/{id}   # revoke token
```

**Create response:**

```json
{
  "id": "uuid",
  "name": "CI pipeline",
  "token": "ai_...",
  "created_at": "2025-06-01T12:00:00Z"
}
```

The `token` value is shown once. Store it securely.

---

## CI/CD integration

Atlas Insight's API is designed for automation. All responses are JSON. The recommended CI/CD workflow:

### 1. Analyze a branch on every push

```bash
#!/usr/bin/env bash
set -euo pipefail

DOMAIN="https://atlas.example.com"
TOKEN="$ATLAS_API_TOKEN"
REPO_URL="https://github.com/${GITHUB_REPOSITORY}"
BRANCH="${GITHUB_HEAD_REF:-${GITHUB_REF_NAME}}"

# Submit
response=$(curl -sf -X POST "$DOMAIN/api/v1/repositories/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"$REPO_URL\",\"branch\":\"$BRANCH\"}")

run_id=$(echo "$response" | jq -r '.run_id')
cached=$(echo "$response" | jq -r '.cached')

echo "Run ID: $run_id  (cached: $cached)"

# Poll until complete
while true; do
  result=$(curl -sf "$DOMAIN/api/v1/repositories/runs/$run_id" \
    -H "Authorization: Bearer $TOKEN")
  status=$(echo "$result" | jq -r '.status')
  echo "Status: $status"
  [[ "$status" == "completed" || "$status" == "failed" ]] && break
  sleep 10
done

if [[ "$status" == "failed" ]]; then
  echo "Analysis failed" >&2
  exit 1
fi

# Extract scores
echo "$result" | jq '{
  oss_score:    .result.heuristics.oss_score,
  health:       .result.heuristics.health_key,
  branch:       .branch,
  commit_sha:   .result.github_meta.sha
}'
```

### 2. Webhook alternative (recommended for long-running analyses)

Pass `webhook_url` on submission and receive a POST when the run finishes:

```json
POST /repositories/analyze
{
  "url": "https://github.com/owner/repo",
  "branch": "feat/my-feature",
  "webhook_url": "https://ci.example.com/atlas-callback"
}
```

See [webhooks.md](webhooks.md) for the callback payload schema.

### 3. Fail the build on poor health

```bash
health=$(echo "$result" | jq -r '.result.heuristics.health_key')
if [[ "$health" == "critical" ]]; then
  echo "::error::Repository health is critical" >&2
  exit 1
fi
```

### GitHub Actions example

```yaml
- name: Atlas Insight analysis
  env:
    ATLAS_API_TOKEN: ${{ secrets.ATLAS_API_TOKEN }}
  run: |
    response=$(curl -sf -X POST \
      "https://atlas.example.com/api/v1/repositories/analyze" \
      -H "Authorization: Bearer $ATLAS_API_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"url\":\"https://github.com/${{ github.repository }}\",\"branch\":\"${{ github.head_ref }}\"}")
    echo "run_id=$(echo $response | jq -r '.run_id')" >> $GITHUB_OUTPUT
```

---

## OpenAPI schema

The full machine-readable schema (OpenAPI 3.x) is served at:

```
GET /api/openapi.json
```

This schema is auto-generated from the live codebase and always reflects the current API.

---

## Error responses

All errors return JSON:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP status | Meaning |
|---|---|
| `400 Bad Request` | Malformed request |
| `403 Forbidden` | Insufficient permissions or unauthenticated |
| `404 Not Found` | Resource does not exist |
| `422 Unprocessable Entity` | Validation error (e.g. invalid GitHub URL) |
| `429 Too Many Requests` | Rate limit exceeded. Check `Retry-After` header |
| `500 Internal Server Error` | Server-side error |

## Rate limits

| Endpoint | Limit |
|---|---|
| `POST /repositories/analyze` | 10 per hour per user/IP |
| `POST /repositories/runs/{id}/retry` | 10 per hour per user/IP |
| `GET /repositories/runs/` | 300 per minute per user/IP |
| `GET /repositories/runs/{id}` | 300 per minute per user/IP |
| `GET /repositories/runs/{id}/branches` | 60 per minute per user/IP |
| JIT endpoints (`/issues`, `/prs`, etc.) | 30 per minute per user/IP |
