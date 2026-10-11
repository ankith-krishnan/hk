import numpy as np
import pytest

from app.ui import callbacks
from app.ui.mock_facade import MockFacade


@pytest.fixture
def facade():
    return MockFacade()


def test_analyze_pair_requires_both_images(facade):
    before = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="AFTER"):
        callbacks.analyze_pair(facade, before, None)
    with pytest.raises(ValueError, match="BEFORE"):
        callbacks.analyze_pair(facade, None, before)


def test_analyze_pair_returns_summary_and_gallery(facade):
    before = np.zeros((16, 16, 3), dtype=np.uint8)
    after = np.full((16, 16, 3), 255, dtype=np.uint8)
    summary, record, gallery = callbacks.analyze_pair(facade, before, after)
    assert "Event #" in summary
    assert record["model_name"] == "MOCK"
    assert len(gallery) >= 2


def test_ask_requires_question(facade):
    with pytest.raises(ValueError, match="Type a question"):
        callbacks.ask(facade, "   ")


def test_ask_returns_evidence_for_keys(facade):
    answer, gallery = callbacks.ask(facade, "Where are my keys?")
    assert "MOCK" in answer
    assert "#1" in answer
    assert gallery


def test_ask_event_number_fixture(facade):
    answer, gallery = callbacks.ask(facade, "Show event #1")
    assert "Event #1" in answer
    assert gallery


def test_enroll_requires_name_and_image(facade):
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="object name"):
        callbacks.enroll_object(facade, "", "alias", image)
    with pytest.raises(ValueError, match="reference image"):
        callbacks.enroll_object(facade, "Wallet", "", None)


def test_load_demo_zones(facade):
    facade.zones.clear()
    message, rows = callbacks.load_zones(facade)
    assert "left_tray" in message.lower() or "loaded 3" in message.lower()
    assert any(row[0] == "left_tray" for row in rows)


def test_save_zone_validates_rectangle(facade):
    with pytest.raises(ValueError, match="rectangle"):
        callbacks.save_zone(facade, "Shelf", "shelf", 0.5, 0.0, 0.2, 1.0)


def test_review_and_correction(facade):
    pending = next(event for event in facade.events if not event.accepted)
    summary = callbacks.decide_event(facade, float(pending.id), "approve")
    assert "Accepted" in summary or "Needs review" not in summary
    corrected = callbacks.correct_event(
        facade,
        pending.id,
        "move",
        "keys",
        "left_tray",
        "center_mat",
    )
    assert "center_mat" in corrected


def test_unknown_or_blank_ids_explain_next_step(facade):
    with pytest.raises(ValueError, match="Enter an event ID"):
        callbacks.decide_event(facade, 0, "approve")
    with pytest.raises(ValueError, match="No event #99"):
        callbacks.decide_event(facade, 99, "reject")
    with pytest.raises(ValueError, match="No event #99"):
        callbacks.correct_event(facade, 99, "move", "keys", "left_tray", "right_tray")
    with pytest.raises(ValueError, match="unknown zone"):
        callbacks.correct_event(facade, 1, "move", "keys", "nowhere", "right_tray")
    with pytest.raises(ValueError, match="No enrolled object"):
        callbacks.delete_object(facade, "wallet")


def test_delete_all_memory_requires_confirmation(facade):
    with pytest.raises(ValueError, match="confirmation"):
        callbacks.delete_all_memory(facade, False)
    message = callbacks.delete_all_memory(facade, True)
    assert "deleted" in message.lower()
    assert facade.events == []


def test_restore_mock_demo_after_delete(facade):
    callbacks.delete_all_memory(facade, True)
    assert facade.events == []
    message = callbacks.restore_mock_demo(facade)
    assert "Restored mock demo" in message
    assert len(facade.events) == 2
    assert facade.objects[0].id == "keys"


def test_export_session_returns_path(facade):
    path = callbacks.export_session(facade)
    assert path.endswith(".json")
