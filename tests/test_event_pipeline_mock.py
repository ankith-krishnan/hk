import json

from app.event_analyzer import EventAnalyzer
from app.schemas import EventContext, ObjectRecord, ZoneRecord
from app.vlm_client import MockVLMClient


def test_mock_event_is_structured_and_allowed(tmp_path):
    composite = tmp_path / "input.jpg"
    composite.write_bytes(b"mock image path is not read by mock client")
    context = EventContext(
        objects=[ObjectRecord(id="keys", display_name="Keys")],
        zones=[
            ZoneRecord(id="left", display_name="Left", polygon=[(0, 0), (0.4, 0), (0.4, 1)]),
            ZoneRecord(id="right", display_name="Right", polygon=[(0.6, 0), (1, 0), (1, 1)]),
        ],
    )
    result, latency, raw = EventAnalyzer(MockVLMClient()).analyze(composite, context)
    assert result.event_type == "move"
    assert result.object_id == "keys"
    assert result.from_zone_id == "left"
    assert result.to_zone_id == "right"
    assert latency == 1
    assert json.loads(raw["responses"][0]["choices"][0]["message"]["content"])["confidence"] == 0.91

