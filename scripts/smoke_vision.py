#!/usr/bin/env python3
"""Prove one-image understanding and BEFORE/AFTER event JSON over local vLLM."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fixtures" / "smoke"


def font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_scene(cube_x: int, path: Path) -> None:
    image = Image.new("RGB", (960, 420), "#f6f4ee")
    draw = ImageDraw.Draw(image)
    title_font = font(34)
    label_font = font(25)
    draw.text((24, 12), "SYNTHETIC WORKSPACE SCENE", fill="#15202b", font=title_font)
    draw.rounded_rectangle((25, 75, 465, 385), radius=18, fill="#e6f0ff", outline="#2f6fb0", width=5)
    draw.rounded_rectangle((495, 75, 935, 385), radius=18, fill="#e9f5e8", outline="#41824a", width=5)
    draw.text((165, 95), "LEFT ZONE", fill="#1c4974", font=label_font)
    draw.text((625, 95), "RIGHT ZONE", fill="#245c2b", font=label_font)
    draw.rounded_rectangle((cube_x, 205, cube_x + 100, 305), radius=8, fill="#d73732", outline="#8c1c1a", width=5)
    draw.text((cube_x + 13, 326), "RED CUBE", fill="#701d1a", font=label_font)
    image.save(path, format="JPEG", quality=92)


def data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def extract_message(response: httpx.Response) -> tuple[str, int, str]:
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    usage = body.get("usage", {})
    if isinstance(content, list):
        content = "\n".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict)
        )
    if not isinstance(content, str) or not content.strip():
        raise ValueError("empty/malformed assistant content")
    return content.strip(), int(usage.get("completion_tokens", 0)), str(body.get("model", "unknown"))


def request(client: httpx.Client, endpoint: str, payload: dict, name: str) -> tuple[str, float, str]:
    started = time.perf_counter()
    response = client.post(endpoint, json=payload)
    latency_ms = (time.perf_counter() - started) * 1000
    print(f"{name}: HTTP {response.status_code}; latency_ms={latency_ms:.1f}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}_raw_response.txt").write_text(response.text, encoding="utf-8")
    if response.status_code != 200:
        raise RuntimeError(f"{name} request failed: {response.text[:1500]}")
    content, completion_tokens, reported_model = extract_message(response)
    print(f"{name}: reported_model={reported_model}; completion_tokens={completion_tokens}\n{content}")
    return content, latency_ms, reported_model


def parse_json(text: str) -> dict:
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise TypeError("event response must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="nvidia/Qwen3.8-27B-NVFP4")
    parser.add_argument("--timeout", type=float, default=240.0)
    args = parser.parse_args()
    if not args.base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        parser.error("The vision smoke test only permits a loopback model endpoint")

    OUT.mkdir(parents=True, exist_ok=True)
    before = OUT / "before_left_cube.jpg"
    after = OUT / "after_right_cube.jpg"
    composite = OUT / "left_to_right_composite.jpg"
    draw_scene(170, before)
    draw_scene(690, after)
    left, right = Image.open(before), Image.open(after)
    panel_width, panel_height = 720, 315
    combined = Image.new("RGB", (panel_width * 2, panel_height + 75), "white")
    draw = ImageDraw.Draw(combined)
    draw.text((25, 8), "BEFORE", fill="#111827", font=font(38))
    draw.text((panel_width + 25, 8), "AFTER", fill="#111827", font=font(38))
    combined.paste(left.resize((panel_width, panel_height)), (0, 60))
    combined.paste(right.resize((panel_width, panel_height)), (panel_width, 60))
    combined.save(composite, format="JPEG", quality=90)

    endpoint = f"{args.base_url.rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=args.timeout) as client:
            description, _, description_model = request(
                client,
                endpoint,
                {
                    "model": args.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Name the visible object and its color."},
                                {"type": "image_url", "image_url": {"url": data_url(before)}},
                            ],
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 96,
                },
                "single_image",
            )
            if "cube" not in description.lower() or "red" not in description.lower():
                raise ValueError("single-image response did not identify the red cube")

            event_text, _, event_model = request(
                client,
                endpoint,
                {
                    "model": args.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Compare this labeled BEFORE/AFTER image. Return only JSON with "
                                        'keys event_type, object_id, from_zone_id, to_zone_id, confidence, '
                                        'visible_evidence, uncertainty_reason. Allowed event_type: move, '
                                        'appear, disappear, no_change, uncertain. Allowed object_id: red_cube. '
                                        "Allowed zones: left_zone, right_zone, outside_view. Use the visible "
                                        "evidence and report the object's movement."
                                    ),
                                },
                                {"type": "image_url", "image_url": {"url": data_url(composite)}},
                            ],
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 256,
                },
                "pair_event",
            )
        event = parse_json(event_text)
        required = {
            "event_type",
            "object_id",
            "from_zone_id",
            "to_zone_id",
            "confidence",
            "visible_evidence",
            "uncertainty_reason",
        }
        missing = required - event.keys()
        if missing:
            raise ValueError(f"event JSON missing keys: {sorted(missing)}")
        moved_left_to_right = (
            event["event_type"] == "move"
            and event["object_id"] == "red_cube"
            and event["from_zone_id"] == "left_zone"
            and event["to_zone_id"] == "right_zone"
        )
        zones_correct = event.get("from_zone_id") == "left_zone" and event.get("to_zone_id") == "right_zone"
        if not (moved_left_to_right or zones_correct):
            raise ValueError(f"model did not identify the expected left-to-right movement: {event}")
        (OUT / "pair_event_parsed.json").write_text(
            json.dumps(event, indent=2), encoding="utf-8"
        )
        reported_models = {description_model, event_model}
        if any(model.lower().startswith("mock") for model in reported_models):
            print(f"MOCK PASS: request format and response validation passed; no model inference performed. Artifacts: {OUT}")
        else:
            print(f"PASS: image request and event response validated from {reported_models}. Artifacts: {OUT}")
        return 0
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
