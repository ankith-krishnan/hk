import numpy as np
import pytest

from app import camera
from app.camera import BrowserPushSource


def test_browser_source_validates_frames_and_rejects_second_live_producer(monkeypatch):
    now = [10.0]
    monkeypatch.setattr(camera.time, "monotonic", lambda: now[0])
    source = BrowserPushSource(max_width=320, stale_seconds=4.0, max_frames=2)
    frame = np.zeros((120, 640, 3), dtype=np.uint8)
    first = source.ingest_frame(frame, "laptop-a")
    assert first["accepted"]
    assert source.latest().shape == (60, 320, 3)
    rejected = source.ingest_frame(frame, "laptop-b")
    assert not rejected["accepted"]
    now[0] = 14.1
    switched = source.ingest_frame(frame, "laptop-b")
    assert switched["accepted"]
    assert switched["source_id"] == "laptop-b"
    assert source.health()["source_disconnects"] == 1
    now[0] = 19.0
    assert not source.health()["connected"]


def test_browser_source_rejects_invalid_or_oversized_frame():
    source = BrowserPushSource()
    with pytest.raises(ValueError):
        source.ingest_frame(np.zeros((4, 4), dtype=np.uint8), "browser")
    with pytest.raises(ValueError):
        source.ingest_frame(np.zeros((1081, 1920, 3), dtype=np.uint8), "browser")

