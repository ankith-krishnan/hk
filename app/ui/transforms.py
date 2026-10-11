"""Convert facade records into compact, readable UI content."""

from __future__ import annotations

from app.schemas import EventRecord, QueryResult, SystemStatus


def is_mock_labeled_model(model_name: str | None) -> bool:
    if not model_name:
        return False
    upper = model_name.upper()
    return upper == "MOCK" or upper.startswith(("MOCK/", "MOCK "))


def event_markdown(event: EventRecord) -> str:
    object_name = event.object_id or "Unknown object"
    transition = f"{event.from_zone_id or 'unknown'} → {event.to_zone_id or 'unknown'}"
    review = "Accepted" if event.accepted else "Needs review / uncertain"
    evidence = " ".join(event.visible_evidence) or event.uncertainty_reason or "No visible evidence supplied."
    mock_banner = ""
    if is_mock_labeled_model(event.model_name):
        mock_banner = "**MOCK · simulated event (fixture evidence)**  \n"
    return (
        f"{mock_banner}### {object_name}: {event.event_type.replace('_', ' ').title()}\n"
        f"**{transition}** · {event.confidence:.0%} confidence · {review} · Event #{event.id}\n\n"
        f"{evidence}"
    )


def query_markdown(result: QueryResult) -> str:
    citations = ", ".join(f"#{event_id}" for event_id in result.event_ids) or "No event citation"
    return f"{result.answer}\n\n**Evidence:** {citations}"


def status_markdown(status: SystemStatus) -> str:
    if status.app_mode == "mock":
        runtime = "MOCK MODE · fixture behavior only"
    else:
        runtime = "LOCAL BACKEND · no cloud inference configured"
    model = "ready" if status.model_ready else "not ready"
    camera = "connected" if status.source_connected else "disconnected"
    age = "—" if status.seconds_since_last_frame is None else f"{status.seconds_since_last_frame:.1f}s"
    return (
        f"**{runtime}**  \n"
        f"Offline mode: `{status.offline_mode}` · Model: `{status.model_name}` ({model})  \n"
        f"Laptop camera: {camera} · last frame age: {age} · frames received: {status.frames_received}  \n"
        f"Events: {status.event_count} · evidence records: {status.evidence_count} · "
        f"temporary cache: {status.temp_cache_files} files / {status.temp_cache_bytes} bytes"
    )

