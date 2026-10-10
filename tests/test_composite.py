import numpy as np
from PIL import Image

from app.composite import build_composite
from app.schemas import ObjectRecord, ZoneRecord


def test_composite_has_expected_panels_and_is_saved(tmp_path):
    before = np.full((240, 320, 3), (240, 20, 20), dtype=np.uint8)
    after = np.full((240, 320, 3), (20, 20, 240), dtype=np.uint8)
    zones = [ZoneRecord(id="left", display_name="Left", polygon=[(0, 0), (0.45, 0), (0.45, 1)])]
    objects = [ObjectRecord(id="keys", display_name="Keys")]
    output = tmp_path / "evidence" / "composite.jpg"
    path = build_composite(before, after, zones, objects, output)
    assert path.exists()
    image = Image.open(path)
    assert image.width >= 640
    assert image.height > 240

