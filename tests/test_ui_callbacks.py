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
    assert "default workspace" in message.lower() and "left tray" in message.lower()
    assert any(row[1] == "left_tray" for row in rows)


def test_save_zone_validates_rectangle(facade):
    with pytest.raises(ValueError, match="Zone bounds must satisfy"):
        callbacks.save_zone(facade, "Shelf", "shelf", 0.5, 0.0, 0.2, 1.0)


def test_mock_save_zone_matches_backend_id_rules(facade):
    with pytest.raises(ValueError, match="lowercase ID"):
        callbacks.save_zone(facade, "Shelf", "Shelf Area", 0, 0, 0.5, 0.5)
    with pytest.raises(ValueError, match="already exists"):
        callbacks.save_zone(facade, "Left", "left_tray", 0, 0, 0.5, 0.5)
    with pytest.raises(ValueError, match="outside_view is reserved"):
        callbacks.save_zone(facade, "Outside", "outside_view", 0, 0, 0.5, 0.5)
    assert "shelf" in callbacks.save_zone(facade, "Shelf", "shelf", 0, 0, 0.5, 0.5)


def test_mock_analyze_requires_two_zones(facade):
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    facade.zones = facade.zones[:1]
    callbacks.enroll_object(facade, "Wallet", "billfold", image)
    with pytest.raises(ValueError, match="Load demo zones"):
        callbacks.analyze_pair(facade, image, image)


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
    with pytest.raises(ValueError, match="unknown from_zone_id"):
        callbacks.correct_event(facade, 1, "move", "keys", "nowhere", "right_tray")
    with pytest.raises(ValueError, match="No enrolled object"):
        callbacks.delete_object(facade, "wallet")
    with pytest.raises(ValueError, match="No active zone"):
        callbacks.delete_zone(facade, "garage")


def test_mock_correction_uses_backend_validation_rules(facade):
    with pytest.raises(ValueError, match="move, appear, disappear, or no_change"):
        callbacks.correct_event(facade, 1, "uncertain", "keys", "left_tray", "right_tray")
    with pytest.raises(ValueError, match="must differ"):
        callbacks.correct_event(facade, 1, "move", "keys", "left_tray", "left_tray")
    with pytest.raises(ValueError, match="appear requires"):
        callbacks.correct_event(facade, 1, "appear", "keys", None, None)
    with pytest.raises(ValueError, match="disappear requires"):
        callbacks.correct_event(facade, 1, "disappear", None, None, None)
    corrected = callbacks.correct_event(facade, 1, "disappear", "keys", "left_tray", "outside_view")
    assert "disappear" in corrected.lower()


def test_mock_location_follows_review_and_correction(facade):
    assert facade.get_current_state()[0]["zone_name"] == "Right Tray"
    callbacks.decide_event(facade, 2, "approve")
    assert facade.get_current_state()[0]["zone_name"] == "Left Tray"
    callbacks.decide_event(facade, 2, "reject")
    callbacks.correct_event(facade, 1, "move", "keys", "right_tray", "center_mat")
    assert facade.get_current_state()[0]["zone_name"] == "Center Mat"
    answer, _ = callbacks.ask(facade, "Where are my keys?")
    assert "Center Mat" in answer


def test_mock_does_not_invent_answers_or_events_after_delete(facade):
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    callbacks.delete_all_memory(facade, True)
    answer, gallery = callbacks.ask(facade, "Where are my keys?")
    assert "Right Tray" not in answer and gallery == []
    with pytest.raises(ValueError, match="Load demo zones"):
        callbacks.analyze_pair(facade, image, image)
    callbacks.load_zones(facade)
    with pytest.raises(ValueError, match="Enroll at least one object"):
        callbacks.analyze_pair(facade, image, image)


def test_mock_rejects_duplicate_enroll(facade):
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="already exists"):
        callbacks.enroll_object(facade, "Keys", "", image)


def test_object_enrollment_matches_real_facade_rules():
    import tempfile
    from pathlib import Path

    from app.config import Settings
    from app.facade import LocalRecallFacadeImpl, normalize_object_id, parse_object_aliases
    from app.ui.mock_facade import MockFacade

    image = np.zeros((8, 8, 3), dtype=np.uint8)
    assert normalize_object_id("Café Keys") == "caf_keys"
    assert parse_object_aliases("b; a, b , c") == ["a", "b", "c"]

    mock = MockFacade()
    real_root = Path(tempfile.mkdtemp())
    real = LocalRecallFacadeImpl(
        Settings(
            data_dir=str(real_root / "data"),
            database_path=str(real_root / "data" / "memory.db"),
            gradio_temp_dir=str(real_root / "tmp"),
            inference_mode="mock",
        ),
        mock=True,
    )
    try:
        with pytest.raises(ValueError, match="beginning with a letter"):
            callbacks.enroll_object(mock, "123 Keys", "", image)
        with pytest.raises(ValueError, match="beginning with a letter"):
            real.enroll_object("123 Keys", "", image)

        mock_record = mock.enroll_object("Café Keys", "house; car", image)
        real_record = real.enroll_object("Café Keys", "house; car", image)
        assert mock_record.id == real_record.id == "caf_keys"
        assert mock_record.aliases == real_record.aliases == ["car", "house"]
    finally:
        real.close()


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
    assert "MOCK" in message and "restored" in message.lower()
    assert len(facade.events) == 2
    assert facade.objects[0].id == "keys"


def test_export_session_returns_path(facade):
    path = callbacks.export_session(facade)
    assert path.endswith(".json")
