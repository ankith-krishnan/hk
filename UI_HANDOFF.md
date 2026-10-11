# Frontend A handoff

## Completed

- Manual BEFORE/AFTER capture is the first and clearest Watch-tab action.
- Optional browser-camera ingress is explicitly labeled as laptop-owned and ingress-only.
- Camera health distinguishes not started, connected, waiting, and stale/disconnected states.
- Event summaries explain the observation, confidence, evidence, model, and whether memory changed.
- Ask output cites saved event IDs and confidence, and displays one gallery item per returned evidence path.
- Memory shows current state, event timeline, review state, and retained event evidence.
- Setup shows configured zones and registered objects without exposing backend filesystem paths.
- System & Privacy explains local inference, SQLite memory, uncertainty handling, and transient Gradio cache behavior.
- Mock mode includes deterministic evidence for the Ask flow and remains independent of the backend facade/model.

## Changed files

- `app/ui/app.py`
- `app/ui/callbacks.py`
- `app/ui/transforms.py`
- `app/ui/mock_facade.py`
- `tests/test_ui_contract.py`

## Verification

- `git diff --check`: passed.
- Python tests, Ruff, and browser launch: not run in this Windows workspace because Python, `.venv`, and WSL are unavailable.

## Integrator checklist

Run from the project’s Python environment:

```bash
python -m app.ui.app --mock --host 127.0.0.1 --port 7861
pytest tests/test_ui_contract.py
ruff check app scripts tests
```

Then check the manual pair flow, Ask evidence gallery, stale-camera status, Setup tables, and narrow laptop layout in a browser.
