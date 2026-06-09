# GitHub Webhook Integration

Atlas Insight accepts GitHub push-event webhooks and automatically triggers a fresh analysis when a push is delivered to a repository that already has an existing run.

---

## How it works

1. You register the Atlas Insight webhook URL on your GitHub repository.
2. GitHub sends a signed `push` event to the endpoint on every push.
3. Atlas Insight verifies the HMAC signature, looks up the repository, and enqueues a new analysis run.
4. The push event is deduplicated by `X-GitHub-Delivery` ID — replaying the same delivery has no effect.

---

## Setup

### 1. Register the webhook on GitHub

In your GitHub repository, go to **Settings → Webhooks → Add webhook** and fill in:

| Field | Value |
|---|---|
| Payload URL | `https://<your-domain>/api/v1/repositories/webhooks/github` |
| Content type | `application/json` |
| Secret | A strong random string — must match `GITHUB_WEBHOOK_SECRET` in your Atlas Insight config |
| Events | Select **Just the push event** |
| Active | ✓ |

### 2. Set the secret in Atlas Insight

Add `GITHUB_WEBHOOK_SECRET` to your `backend/.env`:

```
GITHUB_WEBHOOK_SECRET=your-secret-string-here
```

Restart the Django process after updating the env file.

---

## Signature verification

Every delivery is verified using HMAC-SHA256:

```
X-Hub-Signature-256: sha256=<hex digest>
```

Atlas Insight computes `HMAC-SHA256(secret, raw_body)` and compares it with the header using a constant-time comparison (`hmac.compare_digest`). Requests with a missing or invalid signature are rejected with `400 Bad Request`.

In development (`DEBUG=True`) the secret check is skipped if `GITHUB_WEBHOOK_SECRET` is not set. In production, a missing secret causes a `500` error.

---

## Trigger conditions

A webhook delivery triggers reanalysis only when **all** of the following are true:

- The event type is `push`
- The `repository.html_url` in the payload matches a URL Atlas Insight has already analyzed
- The delivery ID has not been seen in the past hour (deduplication)

All deliveries — including ones that do not trigger reanalysis — are recorded in `WebhookDelivery` and visible in the admin panel.

---

## Delivery log

Every delivery is logged. In the admin panel (`/admin`) you can view:

- Delivery ID
- Event type
- Repository URL
- Whether reanalysis was triggered
- The associated run ID (if triggered)

---

## Limitations

- Only `push` events trigger reanalysis. Other event types (`pull_request`, `issues`, etc.) are accepted and logged but do nothing.
- The webhook only fires for repositories Atlas Insight already knows about. Submitting a new URL is still done through the UI or `POST /api/v1/repositories/analyze`.
- Rate limits on the analysis queue still apply. If a repo is analyzed very frequently via webhooks, runs may queue behind each other.
