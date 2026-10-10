from app.memory_store import MemoryStore
from app.schemas import ObjectRecord, VLMEventResult, ZoneRecord


def setup_store(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    store.add_zone(ZoneRecord(id="left", display_name="Left", polygon=[(0, 0), (0.4, 0), (0.4, 1)]))
    store.add_zone(ZoneRecord(id="right", display_name="Right", polygon=[(0.6, 0), (1, 0), (1, 1)]))
    store.add_object(ObjectRecord(id="keys", display_name="Keys", reference_image_path=None))
    return store


def insert(store, event_type, source, target, *, accepted=True):
    return store.add_event(
        VLMEventResult(
            event_type=event_type,
            object_id="keys",
            from_zone_id=source,
            to_zone_id=target,
            confidence=0.9,
            visible_evidence=["visible test evidence"],
            uncertainty_reason=None,
        ),
        accepted=accepted,
        model_name="test",
        model_latency_ms=5,
        raw_response_json={},
        pre_image_path=None,
        post_image_path=None,
        composite_path=None,
    )


def test_event_insert_updates_state_atomically_and_rebuilds(tmp_path):
    store = setup_store(tmp_path)
    event = insert(store, "move", "left", "right")
    state = store.get_object_state("keys")
    assert event.id == state.last_event_id
    assert state.zone_id == "right"
    store.rebuild_state()
    assert store.get_object_state("keys").zone_id == "right"


def test_no_change_does_not_change_state(tmp_path):
    store = setup_store(tmp_path)
    insert(store, "move", "left", "right")
    insert(store, "no_change", "right", "right")
    assert store.get_object_state("keys").zone_id == "right"


def test_delete_all_preserves_schema_and_clears_rows(tmp_path):
    store = setup_store(tmp_path)
    insert(store, "move", "left", "right")
    store.delete_all_memory()
    store.initialize()
    assert store.integrity_check() == "ok"
    assert store.count_events() == 0
    assert store.list_objects() == []

