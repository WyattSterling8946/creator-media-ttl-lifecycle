from src.media_lifecycle import MediaAsset, lifecycle_days


def test_throwaway_media_gets_a_ttl_but_archived_delivery_does_not():
    preview = MediaAsset("creator-7", "tmp/raw.mp4", "tmp/job.mp4", "deliveries/7.mp4")
    archive = MediaAsset("creator-7", "archive/raw.mp4", "archive/job.mp4", "deliveries/7.mp4", temporary=False)

    assert lifecycle_days(preview) == 7
    assert lifecycle_days(archive) == 0
