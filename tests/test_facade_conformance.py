"""Mock vs LocalRecallFacadeImpl parity for validation, analysis gates, and state."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from app.config import Settings
from app.facade import LocalRecallFacadeImpl
from app.schemas import ZoneRecord
from app.ui.mock_facade import MockFacade
from app.vlm_client import MockVLMClient

IMAGE = np.zeros((240, 320, 3), dtype=np.uint8)
_FACADE_ERRORS = (ValueError, KeyError, RuntimeError, TypeError)


class ReviewBandVLM(MockVLMClient):
    """Returns a review-band move event (not auto-accepted) for state/decision tests."""

    def analyze_event(self, composite_path, context):
        raw, latency, meta = super().analyze_event(composite_path, context)
        payload = json.loads(raw)
        payload["confidence"] = 0.54
        raw = json.dumps(payload)
        return raw, latency, meta


class SteppedConfidenceVLM(MockVLMClient):
    """First analysis auto-accepts; later analyses land in the review band."""

    def __init__(self) -> None:
        self._calls = 0

    def analyze_event(self, composite_path, context):
        raw, latency, meta = super().analyze_event(composite_path, context)
        payload = json.loads(raw)
        payload["confidence"] = 0.91 if self._calls == 0 else 0.54
        self._calls += 1
        raw = json.dumps(payload)
        return raw, latency, meta


@pytest.fixture
def image():
    return IMAGE.copy()


@pytest.fixture
def mock_pair(tmp_path):
    mock = MockFacade()
    settings = Settings(
        data_dir=str(tmp_path / "data"),
        database_path=str(tmp_path / "data" / "memory.db"),
        gradio_temp_dir=str(tmp_path / "tmp"),
        inference_mode="mock",
    )
    real = LocalRecallFacadeImpl(settings, mock=True)
    yield mock, real
    real.close()


def _is_mock(facade: MockFacade | LocalRecallFacadeImpl) -> bool:
    return isinstance(facade, MockFacade)


def _run_both(
    mock: MockFacade,
    real: LocalRecallFacadeImpl,
    operation: Callable[[MockFacade | LocalRecallFacadeImpl], Any],
) -> tuple[Any, Any]:
    outcomes: dict[str, Any] = {}
    errors: dict[str, BaseException] = {}
    for label, facade in (("mock", mock), ("real", real)):
        try:
            outcomes[label] = operation(facade)
        except _FACADE_ERRORS as exc:
            errors[label] = exc
    if errors:
        assert len(errors) == 2, (
            f"Only one facade raised: mock={errors.get('mock')!r}, real={errors.get('real')!r}, "
            f"other result={outcomes!r}"
        )
        raise AssertionError("use assert_both_reject for error cases")
    return outcomes["mock"], outcomes["real"]


def assert_both_reject(
    mock: MockFacade,
    real: LocalRecallFacadeImpl,
    operation: Callable[[MockFacade | LocalRecallFacadeImpl], Any],
    *message_parts: str,
) -> None:
    errors: dict[str, BaseException] = {}
    for label, facade in (("mock", mock), ("real", real)):
        try:
            operation(facade)
            errors[label] = None
        except _FACADE_ERRORS as exc:
            errors[label] = exc
    assert errors.get("mock") is not None, "mock facade should have rejected the operation"
    assert errors.get("real") is not None, "real facade should have rejected the operation"
    mock_exc = errors["mock"]
    real_exc = errors["real"]
    assert type(mock_exc) is type(real_exc), f"{type(mock_exc)} vs {type(real_exc)}: {mock_exc!r} / {real_exc!r}"
    mock_msg = str(mock_exc).lower()
    real_msg = str(real_exc).lower()
    for part in message_parts:
        needle = part.lower()
        assert needle in mock_msg, mock_exc
        assert needle in real_msg, real_exc


def _correction_event_id(facade: MockFacade | LocalRecallFacadeImpl, image: np.ndarray) -> int:
    if _is_mock(facade):
        return 1
    facade.load_demo_zones()
    if not facade.get_objects():
        facade.enroll_object("Keys", "car keys", image)
    events = facade.get_events(limit=10)
    if events:
        return events[0].id
    event = facade.analyze_pair(image, image)
    return event.id


def _object_zone_id(facade: MockFacade | LocalRecallFacadeImpl, object_id: str) -> str | None:
    if _is_mock(facade):
        event = facade._last_location_event(object_id)
        if event is None:
            return None
        if event.event_type == "disappear":
            return "outside_view"
        return event.to_zone_id
    state = facade.store.get_object_state(object_id)
    return state.zone_id if state else None


def _ensure_enrolled(facade: MockFacade | LocalRecallFacadeImpl, image: np.ndarray) -> None:
    if facade.get_objects() if not _is_mock(facade) else facade.objects:
        return
    facade.enroll_object("Wallet", "billfold", image)


def _prepare_analyze(
    facade: MockFacade | LocalRecallFacadeImpl,
    image: np.ndarray,
    zone_templates: list[ZoneRecord],
) -> None:
    if _is_mock(facade):
        facade.zones = [zone.model_copy() for zone in zone_templates]
        facade.objects.clear()
    else:
        facade.delete_all_memory()
        for zone in zone_templates:
            facade.store.add_zone(zone)
    _ensure_enrolled(facade, image)


def _clear_objects(mock: MockFacade, real: LocalRecallFacadeImpl) -> None:
    mock.objects.clear()
    for obj in list(real.get_objects()):
        real.delete_object(obj.id)


# --- Event corrections ---


@pytest.mark.parametrize(
    "call,msg",
    [
        pytest.param(
            lambda eid: ("move", "keys", "left_tray", "left_tray"),
            "must differ",
            id="same_zone_move",
        ),
        pytest.param(
            lambda eid: ("move", "keys", None, "right_tray"),
            "move requires",
            id="missing_source",
        ),
        pytest.param(
            lambda eid: ("move", "keys", "left_tray", None),
            "move requires",
            id="missing_destination",
        ),
        pytest.param(
            lambda eid: ("appear", "keys", None, None),
            "appear requires",
            id="invalid_appear",
        ),
        pytest.param(
            lambda eid: ("disappear", None, None, None),
            "disappear requires",
            id="invalid_disappear",
        ),
        pytest.param(
            lambda eid: ("move", "keys", "left_tray", "not_a_zone"),
            "unknown to_zone_id",
            id="unknown_destination_zone",
        ),
        pytest.param(
            lambda eid: ("uncertain", "keys", "left_tray", "right_tray"),
            "no_change for an accepted correction",
            id="uncertain_type_rejected",
        ),
    ],
)
def test_correction_validation_matches(mock_pair, image, call, msg):
    mock, real = mock_pair

    def op(facade):
        eid = _correction_event_id(facade, image)
        event_type, object_id, from_zone, to_zone = call(eid)
        return facade.correct_event(eid, event_type, object_id, from_zone, to_zone)

    assert_both_reject(mock, real, op, msg)


def test_correction_outside_view_disappear_updates_state(mock_pair, image):
    mock, real = mock_pair

    def op(facade):
        eid = _correction_event_id(facade, image)
        return facade.correct_event(eid, "disappear", "keys", "left_tray", "outside_view")

    mock_event, real_event = _run_both(mock, real, op)
    assert mock_event.accepted and real_event.accepted
    assert mock_event.user_corrected and real_event.user_corrected
    assert mock_event.to_zone_id == real_event.to_zone_id == "outside_view"
    assert _object_zone_id(mock, "keys") == _object_zone_id(real, "keys") == "outside_view"


def test_correction_valid_move_aligns_state(mock_pair, image):
    mock, real = mock_pair

    def op(facade):
        eid = _correction_event_id(facade, image)
        return facade.correct_event(eid, "move", "keys", "right_tray", "center_mat")

    mock_event, real_event = _run_both(mock, real, op)
    for event in (mock_event, real_event):
        assert event.event_type == "move"
        assert event.accepted
        assert event.user_corrected
        assert event.from_zone_id == "right_tray"
        assert event.to_zone_id == "center_mat"
    assert _object_zone_id(mock, "keys") == _object_zone_id(real, "keys") == "center_mat"


# --- Enrollment ---


@pytest.mark.parametrize(
    "name,aliases,msg",
    [
        pytest.param("123 Keys", "", "beginning with a letter", id="numeric_leading_name"),
        pytest.param("Café Keys", "house; car, house", None, id="unicode_name_and_aliases"),
        pytest.param("Keys", "", "already exists", id="duplicate_id"),
    ],
)
def test_enrollment_conformance(mock_pair, image, name, aliases, msg):
    mock, real = mock_pair
    _clear_objects(mock, real)

    if msg:
        for facade in (mock, real):
            facade.enroll_object("Keys", "seed", image)
        assert_both_reject(mock, real, lambda f: f.enroll_object(name, aliases, image), msg)
        return

    def op(facade):
        return facade.enroll_object(name, aliases, image)

    mock_obj, real_obj = _run_both(mock, real, op)
    assert mock_obj.id == real_obj.id == "caf_keys"
    assert mock_obj.aliases == real_obj.aliases == ["car", "house"]


def test_enrollment_alias_parsing(mock_pair, image):
    mock, real = mock_pair
    _clear_objects(mock, real)

    def op(facade):
        return facade.enroll_object("Notebook", "alpha, beta; gamma,alpha", image)

    mock_obj, real_obj = _run_both(mock, real, op)
    assert mock_obj.id == real_obj.id == "notebook"
    assert mock_obj.aliases == real_obj.aliases == ["alpha", "beta", "gamma"]


# --- Zones ---


@pytest.mark.parametrize(
    "args,msg",
    [
        pytest.param(("Shelf", "shelf", 0.5, 0.0, 0.2, 1.0), "zone bounds must satisfy", id="invalid_coordinates"),
        pytest.param(("Shelf", "shelf", 0.2, 0.2, 0.2, 0.8), "zone bounds must satisfy", id="degenerate_rectangle"),
        pytest.param(("Outside", "outside_view", 0.0, 0.0, 0.5, 0.5), "outside_view is reserved", id="reserved_id"),
        pytest.param(("Bad", "Bad ID", 0.0, 0.0, 0.5, 0.5), "lowercase id", id="invalid_zone_id"),
    ],
)
def test_add_zone_rejected(mock_pair, args, msg):
    mock, real = mock_pair
    assert_both_reject(mock, real, lambda f: f.add_zone(*args), msg)


def test_add_zone_valid_boundary(mock_pair):
    mock, real = mock_pair

    def op(facade):
        return facade.add_zone("Full", "full", 0.0, 0.0, 1.0, 1.0)

    mock_zone, real_zone = _run_both(mock, real, op)
    assert mock_zone.id == real_zone.id == "full"
    assert mock_zone.polygon == real_zone.polygon


# --- Analysis ---


@pytest.mark.parametrize(
    "zone_count,msg",
    [
        pytest.param(0, "load demo zones", id="zero_zones"),
        pytest.param(1, "load demo zones", id="one_zone"),
    ],
)
def test_analyze_pair_requires_two_zones(mock_pair, image, zone_count, msg):
    mock, real = mock_pair
    templates = mock.zones[:zone_count]
    _prepare_analyze(mock, image, templates)
    _prepare_analyze(real, image, templates)
    assert_both_reject(mock, real, lambda f: f.analyze_pair(image, image), msg)


def test_analyze_pair_succeeds_with_two_zones(mock_pair, image):
    mock, real = mock_pair
    templates = mock.zones[:2]
    _prepare_analyze(mock, image, templates)
    _prepare_analyze(real, image, templates)

    mock_event, real_event = _run_both(mock, real, lambda f: f.analyze_pair(image, image))
    assert mock_event.event_type == real_event.event_type == "move"
    assert mock_event.accepted and real_event.accepted
    assert mock_event.object_id == real_event.object_id == "wallet"
    assert mock_event.from_zone_id == real_event.from_zone_id
    assert mock_event.to_zone_id == real_event.to_zone_id


def test_analyze_pair_requires_enrolled_object(mock_pair, image):
    mock, real = mock_pair
    _prepare_analyze(mock, image, mock.zones[:2])
    _prepare_analyze(real, image, mock.zones[:2])
    mock.objects.clear()
    for obj in list(real.get_objects()):
        real.delete_object(obj.id)

    assert_both_reject(
        mock,
        real,
        lambda f: f.analyze_pair(image, image),
        "enroll at least one object",
    )


# --- Approve / reject state ---


def test_approve_pending_event_aligns_location(mock_pair, image, tmp_path):
    mock, _real = mock_pair
    mock.approve_event(2)
    mock_pending = next(event for event in mock.get_events(10) if event.id == 2)
    assert mock_pending.accepted
    assert _object_zone_id(mock, "keys") == mock_pending.to_zone_id

    settings = Settings(
        data_dir=str(tmp_path / "data_approve"),
        database_path=str(tmp_path / "data_approve" / "memory.db"),
        gradio_temp_dir=str(tmp_path / "tmp_approve"),
        inference_mode="mock",
    )
    real_review = LocalRecallFacadeImpl(settings, mock=True, vlm_client=ReviewBandVLM())
    try:
        real_review.load_demo_zones()
        real_review.enroll_object("Keys", "car keys", image)
        real_review.analyze_pair(image, image)
        pending = next(event for event in real_review.get_events(10) if not event.accepted)
        real_review.approve_event(pending.id)
        approved = real_review.store.get_event(pending.id)
        assert approved.accepted
        assert real_review.store.get_object_state("keys").zone_id == approved.to_zone_id
    finally:
        real_review.close()


def test_reject_pending_event_keeps_prior_location(mock_pair, image, tmp_path):
    mock, _real = mock_pair
    before = _object_zone_id(mock, "keys")
    mock.reject_event(2)
    assert _object_zone_id(mock, "keys") == before

    settings = Settings(
        data_dir=str(tmp_path / "data_reject"),
        database_path=str(tmp_path / "data_reject" / "memory.db"),
        gradio_temp_dir=str(tmp_path / "tmp_reject"),
        inference_mode="mock",
    )
    real_review = LocalRecallFacadeImpl(settings, mock=True, vlm_client=SteppedConfidenceVLM())
    try:
        real_review.load_demo_zones()
        real_review.enroll_object("Keys", "car keys", image)
        first = real_review.analyze_pair(image, image)
        assert first.accepted
        baseline = real_review.store.get_object_state("keys").zone_id
        second = real_review.analyze_pair(image, image)
        assert not second.accepted
        real_review.reject_event(second.id)
        assert real_review.store.get_object_state("keys").zone_id == baseline
    finally:
        real_review.close()
