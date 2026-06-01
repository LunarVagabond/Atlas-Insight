# Webhooks

Atlas Insight supports two webhook directions: **inbound** (GitHub notifies Atlas Insight when a repo gets new commits) and **outbound** (Atlas Insight posts to your endpoint when an analysis completes).

---

## Inbound — GitHub → Atlas Insight

When a watched repository receives a push, GitHub sends a webhook that triggers automatic re-analysis.

### Setup

1. Go to your GitHub repository → **Settings → Webhooks → Add webhook**
2. Set **Payload URL** to:
   ```
   https://<your-domain>/api/v1/repositories/webhooks/github
   ```
3. Set **Content type** to `application/json`
4. Set **Secret** to the value of your `GITHUB_WEBHOOK_SECRET` env var (see below)
5. Under **Which events**, choose **Just the push event**
6. Click **Add webhook**

### Env var

In `backend/.env`:
```
GITHUB_WEBHOOK_SECRET=your-random-secret-here
```

Generate a random secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

If `GITHUB_WEBHOOK_SECRET` is empty, signature verification is skipped (not recommended for production).

### Behavior

- Atlas Insight only re-analyzes repos that already have a completed analysis run
- The inbound webhook does **not** create new repository records — the repo must already exist in the system
- Push events to repos not tracked by Atlas Insight are silently ignored (200 OK returned)

---

## Outbound — Atlas Insight → your endpoint

When an analysis run completes (or fails), Atlas Insight POSTs a JSON payload to the URL you specify.

### Setup

Pass `webhook_url` in the analyze request:

```bash
curl -X POST https://<your-domain>/api/v1/repositories/analyze \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/owner/repo",
    "webhook_url": "https://your-server.example.com/atlas-callback"
  }'
```

The `webhook_url` is stored on the `AnalysisRun` record. It is not persisted to the `Repository` — each submission can use a different URL.

### Payload

```json
{
  "run_id": "uuid",
  "status": "completed",
  "repo_url": "https://github.com/owner/repo",
  "repo_owner": "owner",
  "repo_name": "repo",
  "completed_at": "2025-06-01T12:34:56.789Z",
  "error": null
}
```

`status` is either `"completed"` or `"failed"`. `error` is a string if `status` is `"failed"`, otherwise `null`.

### Retry / reliability

Outbound webhook calls have a 10-second timeout and are **not retried** on failure. If your endpoint is temporarily unavailable, the callback is lost. For reliable delivery, make your endpoint idempotent and poll `GET /api/v1/repositories/runs/{id}/` as a fallback.

### Request headers

```
Content-Type: application/json
User-Agent: AtlasInsight/1.0
```

No HMAC signature is sent on outbound requests — verify the `run_id` against your own records if you need authenticity.
