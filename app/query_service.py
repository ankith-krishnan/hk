"""Database-first questions with an optional local-model summary fallback."""

from __future__ import annotations

import re
import time

from rapidfuzz import fuzz

from app.memory_store import MemoryStore
from app.schemas import QueryResult
from app.vlm_client import VLMClient


class QueryService:
    def __init__(self, store: MemoryStore, vlm: VLMClient | None = None):
        self.store = store
        self.vlm = vlm

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", value.lower()))

    def _resolve_object(self, text: str) -> dict | None:
        normalized = self._normalize(text)
        rows = self.store.get_state_rows()
        active = self.store.list_objects()
        aliases = {obj.id: obj.aliases for obj in active}
        candidates: list[tuple[int, dict]] = []
        for row in rows:
            names = [row["object_id"], row["display_name"], *aliases.get(row["object_id"], [])]
            for name in names:
                norm_name = self._normalize(name)
                if not norm_name:
                    continue
                if norm_name == normalized or norm_name in normalized or normalized in norm_name:
                    return row
                candidates.append((fuzz.ratio(normalized, norm_name), row))
        if not candidates:
            return None
        score, row = max(candidates, key=lambda item: item[0])
        return row if score >= 86 else None

    def ask(self, question: str) -> QueryResult:
        started = time.perf_counter()
        text = question.strip()
        lower = text.lower()
        result: QueryResult

        event_match = re.search(r"\b(?:event|number|#)\s*#?(\d+)\b", lower)
        if event_match:
            event_id = int(event_match.group(1))
            try:
                event = self.store.get_event(event_id)
            except KeyError:
                result = QueryResult(answer=f"I do not have event #{event_id}.")
            else:
                paths = [
                    path
                    for path in (event.pre_image_path, event.post_image_path, event.composite_path)
                    if path
                ]
                result = QueryResult(
                    answer=(
                        f"Event #{event.id}: {event.event_type} for {event.object_id or 'an unknown object'}; "
                        f"{event.from_zone_id or 'unknown'} → {event.to_zone_id or 'unknown'} "
                        f"(confidence {event.confidence:.0%})."
                    ),
                    event_ids=[event.id],
                    evidence_paths=paths,
                    confidence=event.confidence,
                )
        elif any(phrase in lower for phrase in ("what moved", "most recently", "most recent")):
            event = next(
                (e for e in self.store.list_events(50) if e.accepted and e.event_type in {"move", "appear", "disappear"}),
                None,
            )
            if event is None:
                result = QueryResult(answer="I do not have a reliable accepted object event yet.")
            else:
                result = QueryResult(
                    answer=(
                        f"The most recent accepted event was #{event.id}: {event.object_id} "
                        f"{event.from_zone_id or 'outside view'} → {event.to_zone_id or 'outside view'}."
                    ),
                    event_ids=[event.id],
                    evidence_paths=[p for p in (event.pre_image_path, event.post_image_path) if p],
                    confidence=event.confidence,
                )
        elif any(phrase in lower for phrase in ("list", "all objects", "locations", "where are all")):
            rows = self.store.get_state_rows()
            locations = [
                f"{row['display_name']}: {row['zone_name'] or 'no reliable observed location'}"
                for row in rows
            ]
            result = QueryResult(
                answer="\n".join(locations) if locations else "No objects are enrolled yet."
            )
        elif "where" in lower or "last moved" in lower or "last seen" in lower:
            row = self._resolve_object(text)
            if row is None:
                result = QueryResult(answer="I do not have a reliable observation for that object.")
            elif "last moved" in lower:
                event = next(
                    (
                        event
                        for event in self.store.list_events(1000)
                        if event.accepted and event.object_id == row["object_id"] and event.event_type == "move"
                    ),
                    None,
                )
                if event is None:
                    result = QueryResult(answer=f"I do not have an accepted move recorded for {row['display_name']}.")
                else:
                    result = QueryResult(
                        answer=f"{row['display_name']} was last moved at {event.ended_at.isoformat()} (event #{event.id}).",
                        event_ids=[event.id],
                        evidence_paths=[p for p in (event.pre_image_path, event.post_image_path) if p],
                        confidence=event.confidence,
                    )
            elif row["last_event_id"] is None:
                result = QueryResult(
                    answer=f"I do not have a reliable observation yet for {row['display_name']}."
                )
            else:
                event = self.store.get_event(int(row["last_event_id"]))
                location = row["zone_name"] or "outside the visible workspace"
                result = QueryResult(
                    answer=(
                        f"{row['display_name']} was last observed in {location} "
                        f"(event #{event.id}, confidence {event.confidence:.0%})."
                    ),
                    event_ids=[event.id],
                    evidence_paths=[p for p in (event.pre_image_path, event.post_image_path) if p],
                    confidence=event.confidence,
                )
        elif self.vlm is not None:
            recent = [event.model_dump(mode="json") for event in self.store.list_events(20)]
            answer = self.vlm.answer_from_records(text, recent)
            ids = [int(match) for match in re.findall(r"#(\d+)", answer)]
            event_by_id = {event.id: event for event in self.store.list_events(50)}
            evidence = [
                path
                for event_id in ids
                if event_id in event_by_id
                for path in (event_by_id[event_id].pre_image_path, event_by_id[event_id].post_image_path)
                if path
            ]
            result = QueryResult(answer=answer, event_ids=ids, evidence_paths=evidence)
        else:
            result = QueryResult(answer="I can answer object locations and recent events from saved records.")

        elapsed = round((time.perf_counter() - started) * 1000)
        self.store.insert_query(text, result.answer, result.event_ids, elapsed)
        return result

