"""Mock mode labeling: MOCK on simulated output, backend messages on validation errors."""

import numpy as np
import pytest

from app.ui import callbacks
from app.ui.mock_facade import MOCK_MODEL_NAME, MockFacade
from app.ui.transforms import status_markdown


@pytest.fixture
def facade():
    return MockFacade()


def test_status_banner_is_mock_labeled(facade):
    md = status_markdown(facade.get_status())
    assert "MOCK MODE" in md
    assert facade.get_status().model_name.upper().startswith("MOCK")


def test_ask_answers_are_mock_labeled(facade):
    answer, _ = callbacks.ask(facade, "Where are my keys?")
    assert answer.strip().startswith("MOCK:") or "MOCK ·" in answer or "MOCK:" in answer.split("\n")[0]


def test_event_summary_and_evidence_are_mock_labeled(facade):
    before = np.zeros((16, 16, 3), dtype=np.uint8)
    after = np.full((16, 16, 3), 255, dtype=np.uint8)
    summary, record, _ = callbacks.analyze_pair(facade, before, after)
    assert record["model_name"] == MOCK_MODEL_NAME
    assert "MOCK" in summary
    assert all("MOCK" in line for line in record["visible_evidence"])


def test_validation_errors_do_not_use_mock_prefix(facade):
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(ValueError) as exc:
        facade.enroll_object("123 Keys", "", image)
    assert "MOCK" not in str(exc.value)
    assert "beginning with a letter" in str(exc.value).lower()

    with pytest.raises(ValueError) as exc:
        facade.add_zone("Outside", "outside_view", 0.0, 0.0, 0.5, 0.5)
    assert "MOCK" not in str(exc.value)

    with pytest.raises(ValueError) as exc:
        facade.delete_zone("outside_view")
    assert "MOCK" not in str(exc.value)
    assert "outside_view is reserved" in str(exc.value)


def test_restore_demo_success_message_is_mock_labeled(facade):
    callbacks.delete_all_memory(facade, True)
    message = callbacks.restore_mock_demo(facade)
    assert "MOCK" in message
    assert "reserved" not in message.lower()
