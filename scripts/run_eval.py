#!/usr/bin/env python3
"""Run synthetic or recorded image-pair trials through the event analyzer."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.composite import build_composite
from app.config import Settings
from app.event_analyzer import EventAnalyzer
from app.schemas import EventContext, ObjectRecord, ZoneRecord
from app.vlm_client import MockVLMClient, OpenAICompatibleVLMClient

DEFAULT_MANIFEST = ROOT / "tests/fixtures/trial_manifest.jsonl"
DEFAULT_OUTPUT = ROOT / "data/evaluation/results"
OBJECTS = [
    ObjectRecord(id="red_cube", display_name="Red Cube", aliases=["cube"]),
    ObjectRecord(id="blue_mug", display_name="Blue Mug", aliases=["mug"]),
    ObjectRecord(id="keys", display_name="Keys", aliases=["key ring"]),
    ObjectRecord(id="plant", display_name="Plant", aliases=["small plant"]),
]
ZONES = [
    ZoneRecord(id="left_tray", display_name="Left Tray", polygon=[(0.02, 0.15), (0.32, 0.15), (0.32, 0.92), (0.02, 0.92)]),
    ZoneRecord(id="center_mat", display_name="Center Mat", polygon=[(0.35, 0.15), (0.65, 0.15), (0.65, 0.92), (0.35, 0.92)]),
    ZoneRecord(id="right_tray", display_name="Right Tray", polygon=[(0.68, 0.15), (0.98, 0.15), (0.98, 0.92), (0.68, 0.92)]),
]


def load_manifest(path: Path) -> list[dict]:
    trials = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not trials:
        raise ValueError(f"manifest has no trials: {path}")
    required = {
        "trial_id", "object_id", "expected_event_type", "expected_from_zone", "expected_to_zone", "fixture_path",
        "before_image", "after_image", "expected_ambiguous", "notes",
    }
    ids: set[str] = set()
    for trial in trials:
        missing = required - trial.keys()
        if missing:
            raise ValueError(f"trial missing fields {sorted(missing)}: {trial}")
        if trial["trial_id"] in ids:
            raise ValueError(f"duplicate trial ID: {trial['trial_id']}")
        ids.add(trial["trial_id"])
        for key in ("before_image", "after_image"):
            image_path = Path(trial[key])
            if not image_path.is_absolute():
                image_path = (path.parent / image_path).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"{trial['trial_id']}: image not found: {image_path}")
            trial[key] = str(image_path)
    return trials


def rgb(path: str) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def measure(trials: list[dict], records: list[dict], mode: str) -> dict:
    eligible = [
        (trial, result)
        for trial, result in zip(trials, records, strict=True)
        if not trial["expected_ambiguous"]
    ]
    positive_types = {"move", "appear", "disappear"}
    tp = fp = fn = 0
    for trial, result in eligible:
        expected = trial["expected_event_type"] in positive_types
        predicted = result["predicted_event_type"] in positive_types
        tp += int(expected and predicted)
        fp += int(not expected and predicted)
        fn += int(expected and not predicted)

    def accuracy(field: str, expected_key: str, *, only_expected: bool = False) -> dict:
        rows = [
            (trial, result)
            for trial, result in zip(trials, records, strict=True)
            if not trial["expected_ambiguous"]
            and (not only_expected or trial[expected_key] is not None)
            and trial[expected_key] is not None
        ]
        if not rows:
            return {"value": None, "correct": 0, "total": 0}
        correct = sum(result[field] == trial[expected_key] for trial, result in rows)
        return {"value": correct / len(rows), "correct": correct, "total": len(rows)}

    event_total = len(eligible)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    latencies = [int(item["model_latency_ms"]) for item in records if item.get("model_latency_ms") is not None]
    e2e = [float(item["end_to_end_ms"]) for item in records]
    return {
        "mode": mode,
        "trial_count": len(trials),
        "eligible_event_detection_trials": event_total,
        "ambiguous_trials_excluded_from_binary_detection": sum(bool(t["expected_ambiguous"]) for t in trials),
        "event_precision": precision,
        "event_recall": recall,
        "event_type_accuracy": accuracy("predicted_event_type", "expected_event_type"),
        "object_id_accuracy": accuracy("predicted_object_id", "object_id"),
        "source_zone_accuracy": accuracy("predicted_from_zone", "expected_from_zone"),
        "destination_zone_accuracy": accuracy("predicted_to_zone", "expected_to_zone"),
        "false_positive_count": fp,
        "median_model_latency_ms": None if mode == "mock" or not latencies else statistics.median(latencies),
        "p95_model_latency_ms": None if mode == "mock" or not latencies else sorted(latencies)[min(len(latencies) - 1, int(np.ceil(0.95 * len(latencies))) - 1)],
        "median_end_to_end_latency_ms": statistics.median(e2e) if e2e else None,
        "latency_note": (
            "not measured for real model inference (deterministic mock client)"
            if mode == "mock"
            else "measured end-to-end by this evaluation process"
        ),
        "event_detection_note": "Ambiguous trials are excluded from binary precision/recall; their raw output remains in trial records.",
    }


def render_markdown(summary: dict, results: list[dict]) -> str:
    def display(value) -> str:
        if value is None:
            return "not measured"
        if isinstance(value, dict) and "value" in value:
            return "not measured" if value["value"] is None else f"{value['value']:.1%} ({value['correct']}/{value['total']})"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    metrics = [
        ("Event precision", summary["event_precision"]),
        ("Event recall", summary["event_recall"]),
        ("Event type accuracy", summary["event_type_accuracy"]),
        ("Object ID accuracy", summary["object_id_accuracy"]),
        ("Source zone accuracy", summary["source_zone_accuracy"]),
        ("Destination zone accuracy", summary["destination_zone_accuracy"]),
        ("Median model latency (ms)", summary["median_model_latency_ms"]),
        ("P95 model latency (ms)", summary["p95_model_latency_ms"]),
        ("Median end-to-end latency (ms)", summary["median_end_to_end_latency_ms"]),
        ("False-positive count", summary["false_positive_count"]),
    ]
    lines = [
        "# LocalRecall evaluation",
        "",
        f"- Mode: **{summary['mode']}**",
        f"- Trials: **{summary['trial_count']}**; binary event detection eligible: **{summary['eligible_event_detection_trials']}**",
        f"- Ambiguous trials excluded from binary detection: **{summary['ambiguous_trials_excluded_from_binary_detection']}**",
        "- Synthetic fixture results characterize the selected inference client and harness; they are not a real-world accuracy claim.",
        "",
        "## Metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {display(value)} |" for name, value in metrics)
    lines += ["", summary["latency_note"], "", summary["event_detection_note"], "", "## Trial predictions", "", "| Trial | Expected | Predicted | Object | From | To | ms |", "|---|---|---|---|---|---|---:|"]
    for item in results:
        lines.append(
            f"| {item['trial_id']} | {item['expected_event_type']} | {item['predicted_event_type']} | "
            f"{item['predicted_object_id'] or '—'} | {item['predicted_from_zone'] or '—'} | "
            f"{item['predicted_to_zone'] or '—'} | {item['end_to_end_ms']:.1f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="use deterministic mock inference")
    mode.add_argument("--real", action="store_true", help="use the configured local VLM endpoint")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    is_mock = args.mock
    mode_name = "mock" if is_mock else "real"
    settings = Settings(inference_mode="real", offline_mode=True)
    client = MockVLMClient() if is_mock else OpenAICompatibleVLMClient(settings)
    analyzer = EventAnalyzer(client)
    trials = load_manifest(manifest)
    records = []
    scratch = output_dir / "composites"
    scratch.mkdir(parents=True, exist_ok=True)
    object_map = {obj.id: obj for obj in OBJECTS}
    for trial in trials:
        if trial["object_id"] not in object_map:
            raise ValueError(f"unknown object in trial {trial['trial_id']}: {trial['object_id']}")
        context = EventContext(objects=OBJECTS, zones=ZONES)
        start = time.perf_counter()
        before, after = rgb(trial["before_image"]), rgb(trial["after_image"])
        composite = build_composite(
            before,
            after,
            ZONES,
            OBJECTS,
            scratch / f"{trial['trial_id']}.jpg",
        )
        prediction, latency, raw = analyzer.analyze(composite, context)
        elapsed_ms = (time.perf_counter() - start) * 1000
        records.append(
            {
                "trial_id": trial["trial_id"],
                "fixture_path": trial.get("fixture_path"),
                "expected_event_type": trial["expected_event_type"],
                "expected_object_id": trial["object_id"],
                "expected_from_zone": trial["expected_from_zone"],
                "expected_to_zone": trial["expected_to_zone"],
                "expected_ambiguous": trial["expected_ambiguous"],
                "predicted_event_type": prediction.event_type,
                "predicted_object_id": prediction.object_id,
                "predicted_from_zone": prediction.from_zone_id,
                "predicted_to_zone": prediction.to_zone_id,
                "confidence": prediction.confidence,
                "visible_evidence": prediction.visible_evidence,
                "uncertainty_reason": prediction.uncertainty_reason,
                "model_latency_ms": latency,
                "end_to_end_ms": round(elapsed_ms, 3),
                "raw_response": raw,
            }
        )
    summary = measure(trials, records, mode_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{mode_name}.json"
    markdown_path = output_dir / f"{mode_name}.md"
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest),
        "model_name": client.model_name,
        "summary": summary,
        "trials": records,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(summary, records), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    precision = "not measured" if summary["event_precision"] is None else f"{summary['event_precision']:.3f}"
    recall = "not measured" if summary["event_recall"] is None else f"{summary['event_recall']:.3f}"
    print(f"Trials: {summary['trial_count']}; event precision: {precision}; event recall: {recall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
