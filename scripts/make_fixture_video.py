#!/usr/bin/env python3
"""Generate small deterministic scene pairs and optional fixture videos."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRIALS = [
    ("move_01", "red_cube", "move", "left_tray", "center_mat", False, "Clear move"),
    ("move_02", "blue_mug", "move", "center_mat", "right_tray", False, "Clear move"),
    ("move_03", "keys", "move", "right_tray", "left_tray", False, "Clear move"),
    ("move_04", "plant", "move", "left_tray", "right_tray", False, "Clear move"),
    ("move_05", "red_cube", "move", "center_mat", "left_tray", False, "Clear move"),
    ("move_06", "blue_mug", "move", "right_tray", "center_mat", False, "Clear move"),
    ("move_07", "keys", "move", "left_tray", "right_tray", False, "Clear move"),
    ("move_08", "plant", "move", "right_tray", "left_tray", False, "Clear move"),
    ("move_09", "red_cube", "move", "left_tray", "right_tray", False, "Clear move"),
    ("hand_01", "red_cube", "no_change", "left_tray", "left_tray", False, "Hand passes; object remains"),
    ("hand_02", "blue_mug", "no_change", "center_mat", "center_mat", False, "Hand passes; object remains"),
    ("hand_03", "keys", "no_change", "right_tray", "right_tray", False, "Hand passes; object remains"),
    ("hand_04", "plant", "no_change", "left_tray", "left_tray", False, "Hand passes; object remains"),
    ("appear_01", "blue_mug", "appear", None, "left_tray", False, "Object appears"),
    ("appear_02", "keys", "appear", None, "right_tray", False, "Object appears"),
    ("disappear_01", "plant", "disappear", "center_mat", None, False, "Object disappears"),
    ("disappear_02", "red_cube", "disappear", "right_tray", None, False, "Object disappears"),
    ("ambiguous_01", "keys", "uncertain", "left_tray", "center_mat", True, "Deliberately occluded"),
    ("ambiguous_02", "blue_mug", "uncertain", "right_tray", "center_mat", True, "Deliberately ambiguous"),
    ("no_change_01", "plant", "no_change", "center_mat", "center_mat", False, "Stable scene"),
]
ZONES = {"left_tray": 0, "center_mat": 1, "right_tray": 2}
COLORS = {
    "red_cube": (55, 55, 220),
    "blue_mug": (220, 100, 35),
    "keys": (40, 40, 40),
    "plant": (40, 150, 50),
}


def draw_scene(object_id: str, zone: str | None, *, occluded: bool = False, hand: bool = False) -> np.ndarray:
    image = np.full((480, 960, 3), (242, 240, 232), dtype=np.uint8)
    labels = (("left_tray", "LEFT TRAY"), ("center_mat", "CENTER MAT"), ("right_tray", "RIGHT TRAY"))
    for index, (zone_id, label) in enumerate(labels):
        left, right = 20 + index * 310, 320 + index * 310
        cv2.rectangle(image, (left, 75), (right, 455), (205, 225, 245), 3)
        cv2.putText(image, label, (left + 16, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (45, 55, 65), 2)
        if zone == zone_id:
            center = ((left + right) // 2, 285)
            color = COLORS[object_id]
            if object_id == "keys":
                cv2.circle(image, center, 26, color, -1)
                cv2.circle(image, (center[0] + 38, center[1] + 5), 10, color, 5)
            elif object_id == "plant":
                cv2.rectangle(image, (center[0] - 26, center[1]), (center[0] + 26, center[1] + 52), (90, 95, 120), -1)
                cv2.ellipse(image, (center[0], center[1] - 24), (34, 51), 0, 0, 360, color, -1)
            elif object_id == "blue_mug":
                cv2.rectangle(image, (center[0] - 34, center[1] - 36), (center[0] + 34, center[1] + 36), color, -1)
                cv2.ellipse(image, (center[0] + 39, center[1]), (16, 22), 0, -90, 90, color, 6)
            else:
                cv2.rectangle(image, (center[0] - 35, center[1] - 35), (center[0] + 35, center[1] + 35), color, -1)
            cv2.putText(image, object_id.upper(), (left + 18, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (25, 25, 25), 2)
    if hand:
        cv2.ellipse(image, (485, 270), (60, 28), -12, 0, 360, (160, 175, 190), -1)
        cv2.putText(image, "HAND PASS", (422, 325), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 2)
    if occluded and zone:
        index = ZONES[zone]
        center_x = 170 + index * 310
        cv2.rectangle(image, (center_x - 35, 230), (center_x + 35, 335), (95, 95, 95), -1)
        cv2.putText(image, "OCCLUDED", (center_x - 48, 355), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)
    return image


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"could not write fixture image {path}")


def generate_trials(output_dir: Path, manifest: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for trial_id, object_id, event_type, from_zone, to_zone, ambiguous, notes in TRIALS:
        before_zone = from_zone
        after_zone = to_zone if event_type in {"move", "appear", "no_change"} else None
        hand = trial_id.startswith("hand_")
        occluded = trial_id == "ambiguous_01"
        trial_dir = output_dir / trial_id
        before_path = trial_dir / "before.jpg"
        after_path = trial_dir / "after.jpg"
        save_image(before_path, draw_scene(object_id, before_zone, hand=hand, occluded=occluded))
        save_image(after_path, draw_scene(object_id, after_zone, hand=hand, occluded=occluded))
        rows.append(
            {
                "trial_id": trial_id,
                "object_id": object_id,
                "expected_event_type": event_type,
                "expected_from_zone": from_zone,
                "expected_to_zone": to_zone,
                "fixture_path": os.path.relpath(trial_dir.resolve(), manifest.parent.resolve()),
                "before_image": os.path.relpath(before_path.resolve(), manifest.parent.resolve()),
                "after_image": os.path.relpath(after_path.resolve(), manifest.parent.resolve()),
                "expected_ambiguous": ambiguous,
                "notes": notes,
            }
        )
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def generate_video(path: Path, *, no_change: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (960, 480))
    if not writer.isOpened():
        raise RuntimeError(f"OpenCV could not create {path}")
    try:
        positions = ["left_tray"] * 15 + (["left_tray"] * 20 if no_change else ["center_mat"] * 10 + ["right_tray"] * 15)
        for frame_index, zone in enumerate(positions):
            frame = draw_scene("red_cube", zone)
            cv2.putText(frame, f"FRAME {frame_index:03d}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)
            writer.write(frame)
    finally:
        writer.release()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/evaluation/generated")
    parser.add_argument("--manifest", type=Path, default=ROOT / "tests/fixtures/trial_manifest.jsonl")
    parser.add_argument("--video", action="store_true", help="also generate move.mp4 and no_change.mp4")
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    generate_trials(output_dir, manifest)
    if args.video:
        generate_video(output_dir / "clear_move.mp4")
        generate_video(output_dir / "hand_pass_no_change.mp4", no_change=True)
    print(f"Generated {len(TRIALS)} synthetic BEFORE/AFTER trials at {output_dir}")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()
