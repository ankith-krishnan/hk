# Recorded trial data

Keep user-recorded trials under this directory, one folder per trial, with `before.jpg`, `after.jpg`, and a row in the JSONL manifest. Do not put identifying people or private room content in a public commit. Large original video files stay outside Git; record their local path and generate image pairs using the fixture extraction flow.

Suggested layout:

```text
recorded_trials/
  README.md
  trial_manifest.jsonl
  trial_001/
    before.jpg
    after.jpg
```

Manifest fields are documented by `tests/fixtures/trial_manifest.jsonl`. A real evaluation can be run with:

```bash
.venv/bin/python scripts/run_eval.py --real --manifest tests/fixtures/recorded_trials/trial_manifest.jsonl
```

No real recorded trials are currently available. The checked-in manifest describes deterministic synthetic trials only.
