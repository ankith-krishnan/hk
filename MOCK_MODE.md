# Mock mode labeling and behavior

Mock mode (`python -m app.ui.app --mock`, `MockFacade`) is a **rehearsal** environment: obviously simulated output, but the same input validation as the real backend where practical.

## Labeling (use `MOCK` clearly)

Apply to **answers**, **evidence text**, **status**, and **fixture imagery**:

- Ask/query answers: prefix with `MOCK:` (or `MOCK ·` in UI chrome).
- Event `visible_evidence`, uncertainty copy, and composite fixture labels: include `MOCK` (e.g. `MOCK fixture: …`).
- Event `model_name` in the UI mock path: `MOCK` (backend mock inference may use `mock/…` model ids separately).
- Status banner: `MOCK MODE · fixture behavior only` (see `status_markdown`).
- Session export metadata and demo-restore success copy: state that data is **MOCK** fixture data.

## Validation errors (no `MOCK` prefix)

When the user gives invalid input, raise the **same `ValueError` / `KeyError` messages** as `LocalRecallFacadeImpl` (shared helpers in `app/facade.py`, `validate_event`, `build_zone_record`, `_validate_frame`, etc.).

Do **not** prefix validation failures with `MOCK:` — the user should see the same fix instructions they would see on `--backend`.

## Application behavior

- Enforce the same enrollment, zone, correction, and analyze preconditions as the backend (see `tests/test_facade_conformance.py`).
- Mock-only affordances (restore demo fixtures, deterministic Ask fixtures) must still be labeled as MOCK in **success** messages, not in validation errors.

## Verification

```bash
make test   # includes tests/test_mock_labeling.py and test_facade_conformance.py
```
