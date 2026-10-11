# Frontend A handoff

## Completed

- Manual BEFORE/AFTER capture is the first and clearest Watch-tab action.
- Optional browser-camera ingress is explicitly labeled as laptop-owned and ingress-only.
- Camera health distinguishes not started, connected, waiting, and stale/disconnected states.
- Event summaries explain the observation, confidence, evidence, model, and whether memory changed.
- Ask output cites saved event IDs and confidence, and displays one gallery item per returned evidence path.
- Memory shows current state, event timeline, review state, and retained event evidence.
- Memory timeline includes each event's `started_at` timestamp formatted as UTC.
- Setup shows configured zones and registered objects without exposing backend filesystem paths.
- System & Privacy explains local inference, SQLite memory, uncertainty handling, and transient Gradio cache behavior.
- Mock mode includes deterministic evidence for the Ask flow and remains independent of the backend facade/model.

## Changed files

- `app/ui/app.py`
- `app/ui/callbacks.py`
- `app/ui/transforms.py`
- `app/ui/mock_facade.py`
- `tests/test_ui_contract.py`
- `UI_HANDOFF.md`
- `BACKEND_A.md` removed from this Frontend A branch; Backend A owns that specification.

## Verification

- `.\.venv\Scripts\ruff.exe check --select I --fix tests\test_ui_contract.py`: fixed the import-order issue.
- `.\.venv\Scripts\ruff.exe check app scripts tests`: passed with zero errors.
- `.\.venv\Scripts\python.exe -m pytest`: **25 passed**.
- `.\.venv\Scripts\python.exe -m pytest tests\test_ui_contract.py -q`: **9 passed**.
- `.\.venv\Scripts\python.exe -m app.ui.app --mock --host 127.0.0.1 --port 7861`: launched successfully at `http://127.0.0.1:7861`.
- Browser smoke check: all five tabs rendered; manual BEFORE/AFTER uploads produced mock Event #3 with two evidence thumbnails; mock status, camera health, Setup tables, Ask controls, UTC timeline header, and privacy controls were visible.
- `git diff --check`: passed.

Not verified in this environment: real vLLM inference, backend-mode health traffic, and live laptop camera permission/streaming. The mock server was used for UI validation and did not start a model or initialize persistent backend storage.

## Integrator checklist

Run from the project’s Python environment:

```bash
python -m app.ui.app --mock --host 127.0.0.1 --port 7861
pytest tests/test_ui_contract.py
ruff check app scripts tests
```

Then check the manual pair flow, Ask evidence gallery, stale-camera status, Setup tables, and narrow laptop layout in a browser.
