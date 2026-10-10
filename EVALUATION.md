# Evaluation protocol and current results

`tests/fixtures/trial_manifest.jsonl` is the ground-truth manifest. It covers 20 deterministic synthetic image pairs using four labeled objects and three zones. It includes clear moves, hand-pass/no-change scenes, object appearance/disappearance, and two ambiguous scenes. `scripts/make_fixture_video.py` regenerates the pairs and can create stable/move/no-change MP4 fixtures with `--video`.

Run the harness:

```bash
make eval
# After local Qwen image smoke succeeds:
.venv/bin/python scripts/run_eval.py --real --manifest tests/fixtures/trial_manifest.jsonl
```

The script sends each labeled pair composite directly through `EventAnalyzer` and the selected `VLMClient`; it stores per-trial ground truth, raw response, parsed prediction, model-reported latency, and wall-clock pair-to-parse latency. Ambiguous trials are excluded from binary event precision/recall and remain visible in the raw trial rows. Inaccurate predictions do not cause a failing exit code. Missing files, endpoint failures, and malformed runtime setup do.

## Mock harness run

Command: `.venv/bin/python scripts/make_fixture_video.py --output-dir data/evaluation/generated --manifest tests/fixtures/trial_manifest.jsonl --video && .venv/bin/python scripts/run_eval.py --mock`

Observed result: 20 trials; event precision 0.722 (13 true positives / 18 predicted positives); recall 1.000 (13/13 expected events); event type accuracy 50.0% (9/18); object ID accuracy 27.8% (5/18); source-zone accuracy 37.5% (6/16); destination-zone accuracy 37.5% (6/16); false positives 5; median synthetic harness pair-to-parse time 17.412 ms. The deterministic mock always predicts a move for the first object from the first to the last zone. These values characterize the mock client and fixture harness only; they are not Qwen results or product accuracy claims.

Real model latency, real-model accuracy, real user-recorded trial performance, continuous-video persisted-byte measurement, WAN-off inference, and app end-to-end performance are **not measured**. See generated raw details in `data/evaluation/results/` after running the command; those runtime artifacts are intentionally ignored by Git.
