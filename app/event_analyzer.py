"""Parse and validate VLM event output before it can reach persistent memory."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from app.schemas import EventContext, VLMEventResult
from app.vlm_client import VLMClient


def parse_json_object(text: str) -> dict:
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


def validate_event(value: dict, context: EventContext) -> VLMEventResult:
    result = VLMEventResult.model_validate(value)
    object_ids = {obj.id for obj in context.objects}
    zone_ids = {zone.id for zone in context.zones} | {"outside_view"}
    if result.object_id is not None and result.object_id not in object_ids:
        raise ValueError(f"unknown object ID: {result.object_id}")
    for field_name in ("from_zone_id", "to_zone_id"):
        zone_id = getattr(result, field_name)
        if zone_id is not None and zone_id not in zone_ids:
            raise ValueError(f"unknown {field_name}: {zone_id}")
    if result.event_type == "move":
        if result.object_id is None or result.from_zone_id is None or result.to_zone_id is None:
            raise ValueError("move requires an object and both source and destination zones")
        if result.from_zone_id == result.to_zone_id:
            raise ValueError("move source and destination zones must differ")
    if result.event_type == "appear" and (result.object_id is None or result.to_zone_id is None):
        raise ValueError("appear requires an object and destination zone")
    if result.event_type == "disappear" and result.object_id is None:
        raise ValueError("disappear requires an object ID")
    return result


class EventAnalyzer:
    def __init__(self, client: VLMClient):
        self.client = client

    def analyze(
        self, composite_path: Path, context: EventContext
    ) -> tuple[VLMEventResult, int, dict]:
        response, latency_ms, raw = self.client.analyze_event(composite_path, context)
        responses = [response]
        raw_responses = [raw]
        try:
            return validate_event(parse_json_object(response), context), latency_ms, {
                "responses": raw_responses
            }
        except (ValueError, TypeError, ValidationError, json.JSONDecodeError) as first_error:
            repair, retry_latency, retry_raw = self.client.repair_event(
                composite_path, context, response, str(first_error)
            )
            responses.append(repair)
            raw_responses.append(retry_raw)
            try:
                result = validate_event(parse_json_object(repair), context)
                return result, latency_ms + retry_latency, {
                    "responses": raw_responses,
                    "repaired": True,
                }
            except (ValueError, TypeError, ValidationError, json.JSONDecodeError) as second_error:
                return (
                    VLMEventResult(
                        event_type="uncertain",
                        object_id=None,
                        from_zone_id=None,
                        to_zone_id=None,
                        confidence=0.0,
                        visible_evidence=[],
                        uncertainty_reason=f"invalid model response after repair: {second_error}",
                    ),
                    latency_ms + retry_latency,
                    {
                        "responses": raw_responses,
                        "invalid_text": responses,
                        "repaired": False,
                    },
                )

