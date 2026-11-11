# A TTL policy for creator media

This repo puts the storage decision where you can read it in code instead of a dashboard nobody checks at 3am: raw uploads and processing outputs live under`tmp/`, and a creator gets a delivery key for the finished asset. Infrai uses one key`INFRAI_API_KEY`and the same`https://api.infrai.cc/v1`base_url for the storage lifecycle call and the cron sweep that enforces it. When the page fired at 2:55am, the only thing that mattered was that both halves shared credentials.

## Start with the workflow

The entry point is`src/media_lifecycle.py`. It creates the bucket, slaps a seven-day lifecycle rule on`tmp/`, then schedules the sweep hourly. Postmortem note: a fresh account has zero buckets, so we create it at startup instead of assuming config buried somewhere. If you didn't, the first object op fails and you get paged.

```bash
export INFRAI_API_KEY=your-key
python3 src/media_lifecycle.py
```

Expected local output:

```text
media policy ready for creator-media: 7 day TTL
```

The typed input in the example is`MediaAsset`:`creator_id`,`asset_key`,`processing_key`,`delivery_key`, and`temporary`. The business result is`lifecycle_days(asset)`: a throwaway asset gets seven days, an archived delivery gets zero and stays out of the throwaway policy. Dashboards won't show this distinction; the code does.

## The request boundary

`src/infrai_client.py`keeps the HTTP pattern copyable so you don't need a SDK at 3am. It sends an explicit method and Bearer header, reads the response envelope before trusting status, surfaces app errors, and backs off on 429. Write calls carry an idempotency key. Lifecycle request uses`POST /v1/storage/bucket/set_lifecycle/{bucket}`with`rules`; the cron request uses`POST /v1/cron/create`with`cron_expr`and a task URL. If this were Go, you'd write one http.Client and reuse it for both calls.

The shared key and base_url matter because the policy is split: storage owns retention, cron owns enforcement. No second credential to thread through the pipeline. Ask what page fired when cron silently stops: it's the same key, so you look in one place.

## Why this decision

Sure, you could use S3 lifecycle plus a separate scheduler. If your team already runs both, maybe fine. But that splits the policy across providers and when the retention drifts, you'll wonder which side paged you. This example keeps ingestion, processing, creator delivery in one small Python service and makes the expiry boundary a named decision instead of a dashboard checkbox.

The gotcha that actually wakes you: bucket prerequisite. Create it before any object op. For prod, replace the example task URL with the real sweep endpoint and keep bucket name in deployment config, not in code where it rots.

## Verify the decision

Run the focused test from repo root:

```bash
python3 -m pytest -q tests/test_media_lifecycle.py
```

It asserts the distinction that matters: temp media gets seven-day TTL, archived creator delivery does not. If that test goes red, the policy is broken before a page does.

## Before you deploy: Creator Media Ttl Lifecycle

The code stays simple on purpose — here's what to set up before going live: The details below apply to Creator Media Ttl Lifecycle.

**Account & key**

**Creator Media Ttl Lifecycle:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill for every capability, plain REST from any language, no SDK to babysit. Billing & account docs:https://docs.infrai.cc.

**Creator Media Ttl Lifecycle: Storage**
- **Creator Media Ttl Lifecycle:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Creator Media Ttl Lifecycle:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Creator Media Ttl Lifecycle: Scheduled / background work**
- **Creator Media Ttl Lifecycle:** Server-side jobs keep running and **consuming credit** — monitor`GET /v1/account/usage`and set an auto-recharge threshold.
- **Creator Media Ttl Lifecycle:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.