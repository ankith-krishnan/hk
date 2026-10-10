import pytest
from pydantic import ValidationError

from app.schemas import VLMEventResult, ZoneRecord


def test_zone_requires_normalized_polygon():
    assert ZoneRecord(
        id="desk", display_name="Desk", polygon=[(0, 0), (1, 0), (1, 1)]
    ).id == "desk"
    with pytest.raises(ValidationError):
        ZoneRecord(id="bad", display_name="Bad", polygon=[(0, 0), (2, 0), (1, 1)])


def test_event_confidence_is_bounded():
    with pytest.raises(ValidationError):
        VLMEventResult(
            event_type="move", object_id="keys", from_zone_id="left", to_zone_id="right",
            confidence=1.2, visible_evidence=[], uncertainty_reason=None,
        )

