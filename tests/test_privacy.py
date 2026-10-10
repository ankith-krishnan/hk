import os

import pytest

from app.privacy import directory_stats, prune_transient_cache, validate_transient_dir


def test_transient_cache_prunes_expired_files_and_obeys_size_cap(tmp_path):
    root = tmp_path / "gradio"
    root.mkdir()
    expired = root / "expired.jpg"
    old = root / "old.png"
    new = root / "new.jpg"
    expired.write_bytes(b"expired")
    old.write_bytes(b"old-data")
    new.write_bytes(b"new-data")
    os.utime(expired, (100, 100))
    os.utime(old, (850, 850))
    os.utime(new, (950, 950))

    stats = prune_transient_cache(
        root,
        retention_seconds=200,
        max_bytes=8,
        now=1000,
    )
    assert not expired.exists()
    assert not old.exists()
    assert new.exists()
    assert stats == directory_stats(root) == {"files": 1, "bytes": len(b"new-data")}


def test_transient_dir_rejects_broad_cleanup_targets(tmp_path):
    with pytest.raises(ValueError):
        validate_transient_dir(tmp_path, tmp_path / "data")
    assert validate_transient_dir(tmp_path / "data" / "tmp" / "gradio", tmp_path / "data")

