"""Thin Gradio callback adapters; all application behavior remains in the facade."""

from __future__ import annotations

import numpy as np

from app.contracts import LocalRecallFacade
from app.ui.transforms import event_markdown, query_markdown, status_markdown


def analyze_pair(facade: LocalRecallFacade, before: np.ndarray | None, after: np.ndarray | None):
    if before is None or after is None:
        raise ValueError("Provide both a BEFORE image and an AFTER image.")
    event = facade.analyze_pair(before, after)
    gallery = [
        (path, label)
        for path, label in (
            (event.pre_image_path, "BEFORE evidence"),
            (event.post_image_path, "AFTER evidence"),
            (event.composite_path, "Model comparison"),
        )
        if path
    ]
    return event_markdown(event), event.model_dump(mode="json"), gallery


def ask(facade: LocalRecallFacade, question: str):
    result = facade.ask(question)
    gallery = [(path, f"Evidence for event #{event_id}") for path in result.evidence_paths for event_id in result.event_ids]
    return query_markdown(result), gallery


def load_zones(facade: LocalRecallFacade):
    zones = facade.load_demo_zones()
    return f"Loaded {len(zones)} demo zones: " + ", ".join(zone.display_name for zone in zones)


def enroll_object(facade: LocalRecallFacade, name: str, aliases: str, image: np.ndarray | None):
    if image is None:
        raise ValueError("Choose a reference image for the object.")
    record = facade.enroll_object(name, aliases, image)
    return f"Enrolled **{record.display_name}** as `{record.id}`."


def ingest_browser_frame(facade: LocalRecallFacade, frame: np.ndarray | None, source_id: str):
    if frame is None:
        return "Waiting for the laptop browser camera to start."
    receipt = facade.ingest_frame(frame, source_id)
    if not receipt.get("accepted"):
        return f"Frame rejected: {receipt.get('reason', 'unknown reason')}"
    return f"Frame received · {receipt['frames_received']} total · {receipt['ingest_fps']} fps"


def refresh(facade: LocalRecallFacade):
    status = facade.get_status()
    objects = facade.get_objects()
    state_rows = {row["object_id"]: row for row in facade.get_current_state()}
    events = facade.get_events(12)
    rows = []
    for obj in objects:
        match = state_rows.get(obj.id)
        rows.append(
            [obj.display_name, obj.id, match["zone_name"] if match and match["zone_name"] else "Not observed", match["last_event_id"] if match else None]
        )
    gallery = []
    for event in events:
        for path, label in (
            (event.pre_image_path, "BEFORE"),
            (event.post_image_path, "AFTER"),
            (event.composite_path, "Comparison"),
        ):
            if path:
                gallery.append((path, f"Event #{event.id} · {label}"))
    pending = [
        [event.id, event.object_id or "Unknown", event.event_type, event.confidence, event.from_zone_id, event.to_zone_id]
        for event in events
        if not event.accepted
    ]
    return status_markdown(status), rows, gallery, pending


def decide_event(facade: LocalRecallFacade, event_id: float | None, decision: str):
    if event_id is None:
        raise ValueError("Select an event ID first.")
    event_id = int(event_id)
    event = facade.approve_event(event_id) if decision == "approve" else facade.reject_event(event_id)
    return event_markdown(event)


def start_watch(facade: LocalRecallFacade):
    return status_markdown(facade.start_watch())


def stop_watch(facade: LocalRecallFacade):
    return status_markdown(facade.stop_watch())


def export_session(facade: LocalRecallFacade):
    return str(facade.export_session())


def delete_all_memory(facade: LocalRecallFacade, confirmed: bool):
    if not confirmed:
        raise ValueError("Check the confirmation box before deleting all memory.")
    facade.delete_all_memory()
    return "All enrolled objects, zones, queries, events, and retained evidence were deleted."

