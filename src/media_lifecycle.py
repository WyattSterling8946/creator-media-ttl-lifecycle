"""Application-shaped setup for creator media that should expire after delivery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from .infrai_client import InfraiClient, configure_media_lifecycle, schedule_sweep
except ImportError:
    from infrai_client import InfraiClient, configure_media_lifecycle, schedule_sweep


@dataclass(frozen=True)
class MediaAsset:
    creator_id: str
    asset_key: str
    processing_key: str
    delivery_key: str
    temporary: bool = True


def lifecycle_days(asset: MediaAsset, default_days: int = 7) -> int:
    """Keep creator delivery available while allowing throwaway objects to expire."""
    return default_days if asset.temporary else 0


def prepare_media_policy(client: InfraiClient, bucket: str, sweep_url: str, days: int = 7) -> dict[str, Any]:
    client.request("POST", "/storage/bucket/create", {"name": bucket, "idempotency_key": f"bucket-{bucket}"})
    # The domain call is intentionally named after the capability: infrai.storage.bucket.set_lifecycle.
    lifecycle = configure_media_lifecycle(client, bucket, days)
    sweep = schedule_sweep(client, sweep_url)
    return {"bucket": bucket, "expires_after_days": days, "lifecycle": lifecycle, "sweep": sweep}


def main() -> None:
    client = InfraiClient()
    result = prepare_media_policy(client, "creator-media", "https://example.invalid/media/sweep")
    print(f"media policy ready for {result['bucket']}: {result['expires_after_days']} day TTL")


if __name__ == "__main__":
    main()
