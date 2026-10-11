import numpy as np
import pytest
from app.schemas import QueryResult
from app.ui.app import create_app
from app.ui.callbacks import analyze_pair, ask, refresh_event_rows, refresh_setup_rows
from app.ui.mock_facade import MockFacade
from app.ui.transforms import query_markdown, source_status_markdown



def test_mock_facade_supports_manual_pair_and_database_shaped_answer():
    facade = MockFacade()
    before = np.zeros((32, 32, 3), dtype=np.uint8)
    after = np.full((32, 32, 3), 255, dtype=np.uint8)
    summary, record, gallery = analyze_pair(facade, before, after)
    assert "Event #" in summary
    assert record["model_name"] == "MOCK"
    assert len(gallery) == 2
    response, _ = ask(facade, "Where are my keys?")
    assert "MOCK" in response
    assert "right" in response.lower()


def test_ui_constructs_five_tabs_without_backend_services():
    app = create_app(MockFacade())
    config = app.get_config_file()
    tab_labels = {
        component.get("props", {}).get("label")
        for component in config["components"]
        if component.get("type") == "tabitem"
    }
    assert {"Watch", "Memory", "Ask", "Setup", "System & Privacy"}.issubset(tab_labels)


def test_ui_exposes_manual_pair_camera_health_and_setup_registries():
    app = create_app(MockFacade())
    config_text = str(app.get_config_file())

    assert "Analyze BEFORE + AFTER" in config_text
    assert "Laptop browser frame status" in config_text
    assert "Configured zones" in config_text
    assert "Registered objects" in config_text
    assert "How this local demo works" in config_text


def test_mock_refresh_rows_are_readable_and_do_not_expose_paths():
    facade = MockFacade()

    events = refresh_event_rows(facade)
    zones, objects = refresh_setup_rows(facade)

    assert events[0][0] == 1
    assert events[0][5] == "91%"
    assert zones[0][1] == "left_tray"
    assert objects[0][0] == "Keys"
    assert all("localrecall-mock" not in str(row) for row in objects)


def test_ask_requires_a_question_and_returns_one_gallery_item_per_evidence_path():
    facade = MockFacade()

    response, gallery = ask(facade, "Where are my keys?")

    assert "Confidence" in response
    assert "#1" in response
    assert len(gallery) == 2
    with pytest.raises(ValueError, match="Ask a question"):
        ask(facade, "   ")


def test_source_status_explains_manual_fallback():
    status = MockFacade().get_status()

    rendered = source_status_markdown(status)

    assert "manual" in rendered.lower()
    assert "browser" in rendered.lower()


def test_query_without_evidence_does_not_claim_a_citation():
    rendered = query_markdown(QueryResult(answer="No saved observation.", event_ids=[]))

    assert "No saved event supports" in rendered
    assert "No event citation" not in rendered

