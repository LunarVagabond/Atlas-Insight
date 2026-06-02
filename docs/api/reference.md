# API Reference

Base URL: `https://<your-domain>/api/v1/`

Interactive OpenAPI docs available at `/api/docs` on any running instance.

---

## Authentication

Most endpoints require a Bearer token:

```
Authorization: Bearer <your-token>
```

Public endpoints (badge, read-only run status) do not require authentication.

---

## Endpoints

### Submit a repository for analysis

```
POST /repositories/analyze
```

Submits a GitHub repository URL for analysis. If the repository has been analyzed before and no new commits exist, returns the cached result immediately. Otherwise enqueues a new analysis run.

**Request body:**

```json
{
  "url": "https://github.com/owner/repo",
  "webhook_url": "https://your-server.example.com/callback"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | yes | GitHub repository URL |
| `webhook_url` | string | no | URL to POST to when analysis completes — see [webhooks.md](webhooks.md) |

**Response:**

```json
{
  "run_id": "uuid",
  "status": "queued",
  "cached": false
}
```

`cached: true` means the existing result was returned — no new analysis was enqueued.

---

### Poll run status / get results

```
GET /repositories/runs/{id}/
```

Returns the current state of an analysis run. Poll this after submitting until `status` is `completed` or `failed`.

**Response (in progress):**

```json
{
  "id": "uuid",
  "status": "running",
  "repo_url": "https://github.com/owner/repo",
  "created_at": "2025-06-01T12:00:00Z",
  "completed_at": null,
  "error": null
}
```

**Response (completed):** includes full analysis results nested under `results`.

`status` values: `queued` · `running` · `completed` · `failed`

---

### JIT data endpoints

These endpoints fetch live data from GitHub on-demand and are cached in Redis for 15 minutes.

#### Open issues

```
GET /repositories/runs/{id}/issues
```

Returns open GitHub issues for the repository associated with this run.

#### Open pull requests

```
GET /repositories/runs/{id}/prs
```

Returns open pull requests, including any linked issue references.

#### Delta vs previous run

```
GET /repositories/runs/{id}/diff
```

Returns the delta between this run and the previous one — changes in heuristic scores, dependency counts, structural metrics. Not cached beyond the database.

#### File commit history

```
GET /repositories/runs/{id}/file-history?path=<path>
```

Returns the last 10 commits that touched `<path>`. Fetched from the GitHub API; cached 15 minutes.

| Parameter | Description |
|---|---|
| `path` | File path relative to repo root, e.g. `src/main.py` |

---

### Health badge

```
GET /repositories/badge/{owner}/{name}.svg
```

Returns an SVG badge showing the repository's current OSS Score. Suitable for embedding in a README.

**Example:**

```markdown
![Atlas Insight Score](https://<your-domain>/api/v1/repositories/badge/torvalds/linux.svg)
```

No authentication required.

---

## Polling pattern

```bash
# Submit
RUN_ID=$(curl -s -X POST https://<domain>/api/v1/repositories/analyze \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/owner/repo"}' | jq -r '.run_id')

# Poll until done
while true; do
  STATUS=$(curl -s https://<domain>/api/v1/repositories/runs/$RUN_ID/ \
    -H "Authorization: Bearer <token>" | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] && break
  sleep 5
done
```

Alternatively, pass a `webhook_url` on submission and receive a POST when the run finishes — see [webhooks.md](webhooks.md).
