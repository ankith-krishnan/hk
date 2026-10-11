"""Isolated deterministic mock facade; does not initialize the backend or model."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from app.schemas import EventRecord, ObjectRecord, QueryResult, SystemStatus, ZoneRecord


class MockFacade:
    def __init__(self):
        self.frames_received = 0
        self.watch_mode = False
        self.last_source_time: float | None = None
        self._temp = Path(tempfile.mkdtemp(prefix="localrecall-mock-"))
        self._seed_demo_fixtures()

    def _seed_demo_fixtures(self) -> None:
        self.objects = [ObjectRecord(id="keys", display_name="Keys", aliases=["car keys"])]
        self.zones = [
            ZoneRecord(id="left_tray", display_name="Left Tray", polygon=[(0, 0), (0.3, 0), (0.3, 1)]),
            ZoneRecord(id="center_mat", display_name="Center Mat", polygon=[(0.35, 0), (0.65, 0), (0.65, 1)]),
            ZoneRecord(id="right_tray", display_name="Right Tray", polygon=[(0.7, 0), (1, 0), (1, 1)]),
        ]
        self.events = [
            EventRecord(
                id=1,
                event_type="move",
                object_id="keys",
                from_zone_id="left_tray",
                to_zone_id="right_tray",
                confidence=0.91,
                accepted=True,
                visible_evidence=[
                    "MOCK fixture: keys visible in the left tray before.",
                    "MOCK fixture: keys visible in the right tray after.",
                ],
                model_name="MOCK",
                pre_image_path=None,
                post_image_path=None,
                composite_path=None,
            ),
            EventRecord(
                id=2,
                event_type="move",
                object_id="keys",
                from_zone_id="center_mat",
                to_zone_id="left_tray",
                confidence=0.54,
                accepted=False,
                visible_evidence=["MOCK fixture pending manual review."],
                uncertainty_reason="MOCK review fixture",
                model_name="MOCK",
            ),
        ]
        self._state_zone = "right_tray"
        self._before_path, self._after_path = self._make_evidence()
        self.events[0] = self.events[0].model_copy(
            update={"pre_image_path": str(self._before_path), "post_image_path": str(self._after_path)}
        )

    def restore_demo_fixtures(self) -> None:
        """Reload the default mock zones, Keys object, and sample events after Delete all memory."""
        self._seed_demo_fixtures()
        self.frames_received = 0
        self.watch_mode = False
        self.last_source_time = None

    def _make_evidence(self):
        from PIL import ImageDraw

        paths = []
        for name, object_x in (("before", 70), ("after", 245)):
            image = Image.new("RGB", (360, 210), "#eee9db")
            draw = ImageDraw.Draw(image)
            draw.rectangle((10, 30, 115, 195), fill="#dbeafe", outline="#2563eb", width=3)
            draw.rectangle((245, 30, 350, 195), fill="#dcfce7", outline="#16a34a", width=3)
            draw.text((24, 12), "MOCK · BEFORE / AFTER", fill="#111827")
            draw.ellipse((object_x, 96, object_x + 34, 130), fill="#333333")
            path = self._temp / f"{name}.png"
            image.save(path)
            paths.append(path)
        return paths

    def get_status(self) -> SystemStatus:
        import time

        age = None if self.last_source_time is None else time.monotonic() - self.last_source_time
        return SystemStatus(
            app_mode="mock",
            offline_mode=True,
            model_name="MOCK fixture only",
            model_ready=False,
            model_endpoint="disabled in mock mode",
            source_connected=age is not None and age <= 4,
            source_id="mock-browser" if age is not None and age <= 4 else None,
            seconds_since_last_frame=age,
            frames_received=self.frames_received,
            dropped_frames=0,
            watch_mode=self.watch_mode,
            event_count=len(self.events),
            evidence_count=0,
        )

    def get_latest_frame(self):
        return None

    def ingest_frame(self, frame: np.ndarray, source_id: str) -> dict:
        if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("Frame must be uint8 RGB HxWx3.")
        import time

        self.frames_received += 1
        self.last_source_time = time.monotonic()
        return {"accepted": True, "frames_received": self.frames_received, "ingest_fps": 2.0}

    def analyze_pair(self, before: np.ndarray, after: np.ndarray) -> EventRecord:
        if before is None or after is None:
            raise ValueError("Both images are required")
        event = EventRecord(
            id=max((record.id for record in self.events), default=0) + 1,
            event_type="move",
            object_id="keys",
            from_zone_id="left_tray",
            to_zone_id="right_tray",
            confidence=0.91,
            accepted=True,
            visible_evidence=["MOCK fixture: registered keys moved from left tray to right tray."],
            model_name="MOCK",
            pre_image_path=str(self._before_path),
            post_image_path=str(self._after_path),
        )
        self.events.insert(0, event)
        self._state_zone = "right_tray"
        return event

    def get_objects(self):
        return list(self.objects)

    def get_zones(self):
        return list(self.zones)

    def get_events(self, limit: int = 50):
        return self.events[:limit]

    def get_current_state(self):
        return [
            {
                "object_id": obj.id,
                "display_name": obj.display_name,
                "zone_name": self._state_zone.replace("_", " ").title() if obj.id == "keys" and self.events else None,
                "last_event_id": next((event.id for event in self.events if event.accepted and event.object_id == obj.id), None),
            }
            for obj in self.objects
        ]

    def start_watch(self):
        if self.get_status().source_connected:
            self.watch_mode = True
        else:
            raise RuntimeError("Start the mock webcam stream first.")
        return self.get_status()

    def stop_watch(self):
        self.watch_mode = False
        return self.get_status()

    def _event_evidence_paths(self, event: EventRecord | None) -> list[str]:
        if event is None:
            return []
        return [path for path in (event.pre_image_path, event.post_image_path, event.composite_path) if path]

    def ask(self, question: str):
        import re

        lower = question.lower()
        event_match = re.search(r"\b(?:event|#)\s*#?(\d+)\b", lower)
        if event_match:
            event_id = int(event_match.group(1))
            event = next((item for item in self.events if item.id == event_id), None)
            if event is None:
                return QueryResult(answer=f"MOCK: I do not have event #{event_id}.")
            return QueryResult(
                answer=(
                    f"MOCK: Event #{event.id} — {event.event_type} for {event.object_id or 'unknown'}; "
                    f"{event.from_zone_id or '?'} → {event.to_zone_id or '?'}."
                ),
                event_ids=[event.id],
                evidence_paths=self._event_evidence_paths(event),
                confidence=event.confidence,
            )
        if any(phrase in lower for phrase in ("what moved", "most recently", "most recent")):
            event = next((item for item in self.events if item.accepted), None)
            if event is None:
                return QueryResult(answer="MOCK: no accepted events yet.")
            return QueryResult(
                answer=f"MOCK: most recent accepted event was #{event.id} ({event.object_id}).",
                event_ids=[event.id],
                evidence_paths=self._event_evidence_paths(event),
                confidence=event.confidence,
            )
        if "key" in lower:
            event = next((item for item in self.events if item.accepted), None)
            return QueryResult(
                answer=f"MOCK: Keys were last observed in {self._state_zone.replace('_', ' ').title()}.",
                event_ids=[event.id] if event else [],
                evidence_paths=self._event_evidence_paths(event),
                confidence=event.confidence if event else None,
            )
        return QueryResult(answer="MOCK: no fixture answer for that question.")

    def enroll_object(self, display_name: str, description: str, reference_image: np.ndarray):
        object_id = "".join(char.lower() if char.isalnum() else "_" for char in display_name).strip("_")
        record = ObjectRecord(id=object_id, display_name=display_name, aliases=[description] if description else [])
        self.objects.append(record)
        return record

    def load_demo_zones(self):
        from app.facade import DEFAULT_ZONES

        demo_ids = {zone.id for zone in DEFAULT_ZONES}
        custom = [zone for zone in self.zones if zone.id not in demo_ids]
        self.zones = list(DEFAULT_ZONES) + custom
        return list(self.zones)

    def add_zone(self, display_name, zone_id, x1, y1, x2, y2):
        record = ZoneRecord(
            id=zone_id,
            display_name=display_name,
            polygon=[(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
        )
        self.zones.append(record)
        return record

    def delete_object(self, object_id: str):
        if not any(obj.id == object_id for obj in self.objects):
            raise KeyError(f"object {object_id} not found")
        self.objects = [obj for obj in self.objects if obj.id != object_id]
        if not self.objects:
            self._state_zone = ""

    def delete_zone(self, zone_id: str):
        self.zones = [zone for zone in self.zones if zone.id != zone_id]

    def approve_event(self, event_id: int):
        return self._set_decision(event_id, True)

    def reject_event(self, event_id: int):
        return self._set_decision(event_id, False)

    def correct_event(self, event_id, event_type, object_id, from_zone_id, to_zone_id):
        if object_id is not None and object_id not in {obj.id for obj in self.objects}:
            raise ValueError(f"MOCK: unknown object ID `{object_id}`.")
        zone_ids = {zone.id for zone in self.zones}
        for zone_id in (from_zone_id, to_zone_id):
            if zone_id is not None and zone_id not in zone_ids:
                raise ValueError(f"MOCK: unknown zone ID `{zone_id}`.")
        for index, event in enumerate(self.events):
            if event.id == event_id:
                changed = event.model_copy(
                    update={
                        "event_type": event_type,
                        "object_id": object_id,
                        "from_zone_id": from_zone_id,
                        "to_zone_id": to_zone_id,
                        "accepted": True,
                        "user_corrected": True,
                    }
                )
                self.events[index] = changed
                return changed
        raise KeyError(event_id)

    def _set_decision(self, event_id: int, accepted: bool):
        for index, event in enumerate(self.events):
            if event.id == event_id:
                changed = event.model_copy(update={"accepted": accepted})
                self.events[index] = changed
                return changed
        raise KeyError(event_id)

    def get_health(self):
        return {"mode": "mock", "model_ready": False, "event_count": len(self.events)}

    def export_session(self):
        path = self._temp / "mock-session.json"
        path.write_text("MOCK fixture export", encoding="utf-8")
        return path

    def delete_all_memory(self):
        self.events.clear()
        self.objects.clear()
        self.zones.clear()

