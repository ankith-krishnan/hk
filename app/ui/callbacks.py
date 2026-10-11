"""Thin Gradio callback adapters; all application behavior remains in the facade."""

from __future__ import annotations

import numpy as np

from app.contracts import LocalRecallFacade
from app.ui.transforms import (
    event_markdown,
    event_rows,
    object_rows,
    query_markdown,
    source_status_markdown,
    status_markdown,
    zone_rows,
)


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
    question = question.strip()
    if not question:
        raise ValueError("Ask a question such as ‘Where are my keys?’.")
    result = facade.ask(question)
    if result.event_ids:
        cited = ", ".join(f"#{event_id}" for event_id in result.event_ids)
        gallery = [(path, f"Evidence for event(s) {cited}") for path in result.evidence_paths]
    else:
        gallery = []
    return query_markdown(result), gallery


def load_zones(facade: LocalRecallFacade):
    zones = facade.load_demo_zones()
    if not zones:
        return "No demo zones are available. Check backend or mock fixture setup."
    names = ", ".join(zone.display_name for zone in zones)
    return f"**{len(zones)} demo zone(s) ready:** {names}."


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


def refresh(facade: LocalRecallFacade, *, status=None):
    status = status or facade.get_status()
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


def refresh_event_rows(facade: LocalRecallFacade):
    """Return the timeline rows used by the Memory tab."""

    return event_rows(facade.get_events(12))


def refresh_setup_rows(facade: LocalRecallFacade):
    """Return setup registries without leaking backend filesystem paths."""

    return zone_rows(facade.get_zones()), object_rows(facade.get_objects())


def refresh_source_status(facade: LocalRecallFacade, *, status=None):
    """Return only cheap browser-ingress health for the Watch tab."""

    return source_status_markdown(status or facade.get_status())


def refresh_all(facade: LocalRecallFacade):
    """Build every timer-refresh output from one shared system-status read."""

    status = facade.get_status()
    status_text, objects, gallery, pending = refresh(facade, status=status)
    events = refresh_event_rows(facade)
    zones, registered_objects = refresh_setup_rows(facade)
    source = refresh_source_status(facade, status=status)
    return (
        status_text,
        status_text,
        source,
        source,
        objects,
        events,
        gallery,
        pending,
        zones,
        registered_objects,
    )


def decide_event(facade: LocalRecallFacade, event_id: float | None, decision: str):
    if event_id is None:
        raise ValueError("Select an event ID first.")
    event_id = int(event_id)
    event = facade.approve_event(event_id) if decision == "approve" else facade.reject_event(event_id)
    return event_markdown(event)


def correct_event(facade, event_id, event_type, object_id, from_zone_id, to_zone_id):
    if event_id is None:
        raise ValueError("Select an event ID first.")
    event = facade.correct_event(
        int(event_id),
        event_type,
        object_id.strip() or None,
        from_zone_id.strip() or None,
        to_zone_id.strip() or None,
    )
    return event_markdown(event)


def delete_object(facade, object_id):
    if not object_id.strip():
        raise ValueError("Enter the object ID to delete.")
    facade.delete_object(object_id.strip())
    return f"Deleted object reference `{object_id.strip()}`. Historical events remain in the timeline."


def delete_zone(facade, zone_id):
    if not zone_id.strip():
        raise ValueError("Enter the zone ID to delete.")
    facade.delete_zone(zone_id.strip())
    return f"Disabled zone `{zone_id.strip()}`. Historical event evidence remains available."


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

