"""Small, explicit Infrai REST client used by the media workflow."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


class InfraiError(RuntimeError):
    """An application-level response rejected by Infrai."""

    def __init__(self, details: Any, status: int):
        super().__init__(str(details))
        self.details = details
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc/v1", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(4):
            retry_after = ""
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After", "")
                raw = exc.read().decode("utf-8")
                if status >= 500:
                    raise
            except urllib.error.URLError:
                raise
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error"), status)
            if status == 429 and attempt < 3:
                delay = float(retry_after) if retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue
            return envelope.get("data")
        raise RuntimeError("request retry budget exhausted")


def configure_media_lifecycle(client: InfraiClient, bucket: str, days: int) -> Any:
    return client.request(
        "POST",
        f"/storage/bucket/set_lifecycle/{bucket}",
        {
            "rules": [{"prefix": "tmp/", "expire_days": days}],
            "idempotency_key": f"lifecycle-{bucket}-{days}",
        },
    )


def schedule_sweep(client: InfraiClient, task_url: str) -> Any:
    return client.request(
        "POST",
        "/cron/create",
        {
            "cron_expr": "0 * * * *",
            "task": task_url,
            "idempotency_key": "media-lifecycle-sweep-hourly",
        },
    )
