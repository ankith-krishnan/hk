import numpy as np

from app.config import Settings
from app.facade import LocalRecallFacadeImpl


def test_manual_pair_mock_pipeline_persists_event_and_ask_evidence(tmp_path):
    settings = Settings(
        data_dir=str(tmp_path / "data"),
        database_path=str(tmp_path / "data" / "memory.db"),
        gradio_temp_dir=str(tmp_path / "data" / "tmp"),
        inference_mode="mock",
    )
    facade = LocalRecallFacadeImpl(settings, mock=True)
    facade.load_demo_zones()
    reference = np.full((240, 320, 3), 120, dtype=np.uint8)
    facade.enroll_object("Keys", "car keys; house keys", reference)
    before = np.full((240, 320, 3), 90, dtype=np.uint8)
    after = np.full((240, 320, 3), 140, dtype=np.uint8)
    event = facade.analyze_pair(before, after)
    assert event.accepted
    assert event.pre_image_path and event.post_image_path and event.composite_path
    assert facade.store.get_object_state("keys").zone_id == "right_tray"
    answer = facade.ask("Where are my keys?")
    assert "Right Tray" in answer.answer
    assert answer.event_ids == [event.id]
    assert answer.evidence_paths
    last_move = facade.ask("When were the keys last moved?")
    assert last_move.event_ids == [event.id]
    assert "last moved at" in last_move.answer
    corrected = facade.correct_event(event.id, "move", "keys", "right_tray", "left_tray")
    assert corrected.user_corrected and corrected.accepted
    assert facade.store.get_object_state("keys").zone_id == "left_tray"
    facade.delete_all_memory()
    assert facade.get_events() == []
    assert facade.get_objects() == []
    assert facade.store.integrity_check() == "ok"
    facade.close()

