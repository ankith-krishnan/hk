import json

from scripts.make_fixture_video import generate_trials
from scripts.run_eval import load_manifest, measure


def test_fixture_generator_writes_portable_pairs_and_manifest(tmp_path):
    fixture_root = tmp_path / "generated"
    manifest = tmp_path / "trial_manifest.jsonl"
    generate_trials(fixture_root, manifest)

    trials = load_manifest(manifest)
    assert len(trials) == 20
    assert {row["expected_event_type"] for row in trials} >= {
        "move", "no_change", "appear", "disappear", "uncertain"
    }
    assert all(row["fixture_path"] for row in trials)
    assert all(row["before_image"].endswith("before.jpg") for row in trials)
    assert all(row["after_image"].endswith("after.jpg") for row in trials)


def test_evaluation_metrics_exclude_ambiguous_binary_trials():
    trials = [
        {"expected_event_type": "move", "expected_ambiguous": False, "object_id": "keys", "expected_from_zone": "left", "expected_to_zone": "right"},
        {"expected_event_type": "no_change", "expected_ambiguous": False, "object_id": "keys", "expected_from_zone": "left", "expected_to_zone": "left"},
        {"expected_event_type": "uncertain", "expected_ambiguous": True, "object_id": "keys", "expected_from_zone": "left", "expected_to_zone": "right"},
    ]
    records = [
        {"predicted_event_type": trial["expected_event_type"], "predicted_object_id": "keys", "predicted_from_zone": trial["expected_from_zone"], "predicted_to_zone": trial["expected_to_zone"], "model_latency_ms": 1, "end_to_end_ms": 2.0}
        for trial in trials
    ]

    result = measure(trials, records, "real")

    assert result["eligible_event_detection_trials"] == 2
    assert result["ambiguous_trials_excluded_from_binary_detection"] == 1
    assert result["event_precision"] == result["event_recall"] == 1.0
    assert result["false_positive_count"] == 0
    assert result["median_model_latency_ms"] == 1
    assert json.loads(json.dumps(result))["event_type_accuracy"]["correct"] == 2

