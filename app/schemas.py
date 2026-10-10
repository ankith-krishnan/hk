"""Validated application records shared by backend services and the UI."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EventType = Literal["move", "appear", "disappear", "no_change", "uncertain"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class ObjectRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    reference_image_path: str | None = None
    active: bool = True


class ZoneRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    polygon: list[tuple[float, float]]
    active: bool = True

    @field_validator("polygon")
    @classmethod
    def normalized_polygon(cls, value: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(value) < 3:
            raise ValueError("zone polygons require at least three points")
        if any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in value):
            raise ValueError("zone coordinates must be normalized to [0, 1]")
        return value


class VLMEventResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    object_id: str | None
    from_zone_id: str | None
    to_zone_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    visible_evidence: list[str] = Field(default_factory=list, max_length=8)
    uncertainty_reason: str | None = None


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime = Field(default_factory=utc_now)
    event_type: EventType
    object_id: str | None = None
    from_zone_id: str | None = None
    to_zone_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    accepted: bool = False
    user_corrected: bool = False
    visible_evidence: list[str] = Field(default_factory=list)
    uncertainty_reason: str | None = None
    pre_image_path: str | None = None
    post_image_path: str | None = None
    composite_path: str | None = None
    model_name: str = "mock"
    prompt_version: str = "event-v1"
    model_latency_ms: int | None = None
    raw_response_json: dict = Field(default_factory=dict)


class ObjectState(BaseModel):
    object_id: str
    zone_id: str | None = None
    last_event_id: int | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    updated_at: datetime = Field(default_factory=utc_now)


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class QueryResponse(BaseModel):
    answer: str
    event_ids: list[int] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class SystemStatus(BaseModel):
    app_mode: Literal["mock", "backend"]
    offline_mode: bool
    model_name: str
    model_ready: bool
    model_endpoint: str
    source_connected: bool = False
    source_id: str | None = None
    seconds_since_last_frame: float | None = None
    frames_received: int = 0
    dropped_frames: int = 0
    watch_mode: bool = False
    event_count: int = 0
    evidence_count: int = 0
    temp_cache_files: int = 0
    temp_cache_bytes: int = 0
    last_error: str | None = None


class EventContext(BaseModel):
    objects: list[ObjectRecord]
    zones: list[ZoneRecord]


class QueryResult(QueryResponse):
    pass

