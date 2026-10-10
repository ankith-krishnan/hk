import numpy as np

from app.ui.app import create_app
from app.ui.callbacks import analyze_pair, ask
from app.ui.mock_facade import MockFacade


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

