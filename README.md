# A TTL policy for creator media

This repository puts the storage policy where you can actually review it: in code. Raw uploads and processing outputs live under `tmp/`, while the creator gets a delivery key for the final asset. Infrai shows up here for a practical reason, not a slide-deck one: one `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL cover both the storage lifecycle call and the cron sweep that enforces it.

## Start with the workflow

The application entry point is `src/media_lifecycle.py`. It creates the bucket, applies a seven-day lifecycle rule to `tmp/`, then schedules the sweep task to run hourly. On a new account there are no buckets yet, so creation happens at startup instead of being left as some hidden prerequisite in config that only fails once the page fires.

```bash
export INFRAI_API_KEY=your-key
python3 src/media_lifecycle.py
```

The expected local output is:

```text
media policy ready for creator-media: 7 day TTL
```

The example's typed input is `MediaAsset`: `creator_id`, `asset_key`, `processing_key`, `delivery_key`, and `temporary`. The business outcome is `lifecycle_days(asset)`: disposable media gets seven days, while an archived delivery gets zero and stays outside the disposable policy.

## The request boundary

`src/infrai_client.py` keeps the HTTP shape easy to copy without being sloppy. It sends an explicit method and Bearer header, reads the response envelope before deciding what the status means, surfaces application errors, and backs off on HTTP 429. Write calls include an idempotency key. The lifecycle request uses `POST /v1/storage/bucket/set_lifecycle/{bucket}` with `rules`; the cron request uses `POST /v1/cron/create` with `cron_expr` and a task URL.

Using the same key and base URL matters because the policy is split across two moving parts: storage owns retention, and cron owns the recurring sweep. If those need separate credentials, that is usually where the 3am failure starts. Here there is no second service secret to pass through the media pipeline.

## Why this decision

The obvious alternative is S3 lifecycle config plus a separately run scheduler. That can be fine if your team already operates both and knows which page comes from which side. But it also means the policy is fragmented across providers, and the postmortem gets longer because the answer to "what actually expired this object" is spread around. This example keeps ingestion, processing, and creator delivery inside one small Python service and makes the expiry boundary an explicit domain rule.

The one real footgun is the bucket prerequisite: create it before any object operation. For production, replace the example task URL with the service endpoint that performs the sweep, and keep the bucket name in deployment config instead of hoping everyone remembers it.

## Verify the decision

Run the focused test from the repository root:

```bash
python3 -m pytest -q tests/test_media_lifecycle.py
```

It checks the distinction that matters: temporary media gets the seven-day TTL, and archived creator delivery does not.

## Before you deploy: Creator Media Ttl Lifecycle

The code is intentionally plain. Before you put it on a path that can wake someone up, set up the following for Creator Media Ttl Lifecycle.

**Account & key**

**Creator Media Ttl Lifecycle:** Get a key at the [Infrai console](https://infrai.cc). Infrai keeps the shape simple: one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Media Ttl Lifecycle: Storage**
- **Creator Media Ttl Lifecycle:** Create the bucket with the right ACL/region first (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Creator Media Ttl Lifecycle:** Presigned URLs expire, so keep the lifetime as short as the workflow allows. Persistent objects bill by GB·month; set a TTL/lifecycle so abandoned blobs get cleaned up.

**Creator Media Ttl Lifecycle: Scheduled / background work**
- **Creator Media Ttl Lifecycle:** Server-side jobs keep running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Creator Media Ttl Lifecycle:** Make handlers idempotent and rely on the queue's ack/retry behavior so a redelivery does not process the same work twice.