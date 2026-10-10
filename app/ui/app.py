"""LocalRecall Gradio Blocks app for local backend or isolated mock mode."""

from __future__ import annotations

import argparse
import atexit
import os
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values

configured_temp_dir = os.environ.get("GRADIO_TEMP_DIR") or dotenv_values(".env").get("GRADIO_TEMP_DIR")
os.environ.setdefault(
    "GRADIO_TEMP_DIR",
    str(Path(configured_temp_dir or "./data/tmp/gradio").expanduser().resolve()),
)

import gradio as gr

from app.config import Settings
from app.facade import LocalRecallFacadeImpl
from app.ui import callbacks
from app.ui.mock_facade import MockFacade


def create_app(facade, *, temp_allowed_path: str | None = None) -> gr.Blocks:
    data_path = Path("./data").resolve()
    allowed_paths = [str(data_path)]
    if temp_allowed_path:
        allowed_paths.append(temp_allowed_path)
    css = """
    .gradio-container { max-width: 1240px !important; }
    .lr-header { padding: 1.25rem 1.5rem; border-radius: 16px; background: #f1f5f9; }
    .lr-note { color: #475569; font-size: 0.95rem; }
    """
    with gr.Blocks(title="LocalRecall", css=css, theme=gr.themes.Soft()) as demo:
        source_id = gr.State(value="")
        gr.Markdown(
            "# LocalRecall\n**Private visual memory for a bounded workspace.** "
            "Images are analyzed by the local backend and event facts live in SQLite.",
            elem_classes=["lr-header"],
        )
        status_line = gr.Markdown()

        with gr.Tabs():
            with gr.Tab("Watch"):
                gr.Markdown(
                    "Use two snapshots or uploads for the dependable manual path. "
                    "The optional browser stream sends frames to the GB10 over your local connection. "
                    "Automatic event detection is not enabled yet; this stream currently reports ingress health only.",
                    elem_classes=["lr-note"],
                )
                with gr.Row():
                    browser_camera = gr.Image(
                        label="Laptop Camera · optional live stream",
                        sources=["webcam"],
                        type="numpy",
                        streaming=True,
                    )
                    with gr.Column():
                        ingest_status = gr.Markdown("Camera disconnected. Upload pairs below any time.")
                        with gr.Row():
                            watch_start = gr.Button("Start Watch", variant="secondary")
                            watch_stop = gr.Button("Stop Watch")
                gr.Markdown("## Manual Remember · BEFORE / AFTER")
                with gr.Row():
                    before = gr.Image(
                        label="BEFORE · webcam snapshot or image upload",
                        sources=["webcam", "upload"],
                        type="numpy",
                    )
                    after = gr.Image(
                        label="AFTER · webcam snapshot or image upload",
                        sources=["webcam", "upload"],
                        type="numpy",
                    )
                analyze_button = gr.Button("Analyze Change", variant="primary")
                event_summary = gr.Markdown("Add both images, then analyze the change.")
                event_details = gr.JSON(label="Event details")
                event_evidence = gr.Gallery(label="BEFORE / AFTER evidence", columns=3, height=260)

            with gr.Tab("Memory"):
                with gr.Row():
                    object_table = gr.Dataframe(
                        headers=["Object", "ID", "Current location", "Last event"],
                        label="Current object state",
                        interactive=False,
                    )
                    event_table = gr.Dataframe(
                        headers=["Event", "Object", "Type", "From", "To", "Confidence", "Accepted"],
                        label="Recent event timeline",
                        interactive=False,
                    )
                review_table = gr.Dataframe(
                    headers=["Event ID", "Object", "Type", "Confidence", "From", "To"],
                    label="Events awaiting review",
                    interactive=False,
                )
                with gr.Row():
                    review_id = gr.Number(label="Event ID to review", precision=0)
                    approve = gr.Button("Approve event")
                    reject = gr.Button("Reject event")
                review_result = gr.Markdown()
                memory_gallery = gr.Gallery(label="Saved event evidence", columns=4, height=300)

            with gr.Tab("Ask"):
                question = gr.Textbox(
                    label="Ask about your workspace",
                    placeholder="Where are my keys?",
                    lines=2,
                )
                with gr.Row():
                    ask_button = gr.Button("Ask LocalRecall", variant="primary")
                    gr.Examples(
                        examples=["Where are my keys?", "What moved most recently?", "Show event #1"],
                        inputs=question,
                    )
                answer = gr.Markdown()
                ask_evidence = gr.Gallery(label="Answer evidence", columns=3, height=260)

            with gr.Tab("Setup"):
                gr.Markdown("Enroll a few recognizable objects and keep zones aligned with the camera view.")
                with gr.Row():
                    object_name = gr.Textbox(label="Object name", placeholder="Keys")
                    object_aliases = gr.Textbox(label="Aliases, separated by commas", placeholder="car keys, key ring")
                reference = gr.Image(
                    label="Object reference image · upload or browser snapshot",
                    sources=["webcam", "upload"],
                    type="numpy",
                )
                enroll_button = gr.Button("Enroll object")
                setup_result = gr.Markdown()
                zones_button = gr.Button("Load three demo zones", variant="secondary")
                zone_result = gr.Markdown()
                gr.Markdown("### Add a rectangular zone")
                with gr.Row():
                    zone_name = gr.Textbox(label="Zone name", placeholder="Shelf")
                    zone_slug = gr.Textbox(label="Zone ID", placeholder="shelf")
                with gr.Row():
                    x1 = gr.Number(label="x1", value=0.0, minimum=0, maximum=1)
                    y1 = gr.Number(label="y1", value=0.0, minimum=0, maximum=1)
                    x2 = gr.Number(label="x2", value=1.0, minimum=0, maximum=1)
                    y2 = gr.Number(label="y2", value=1.0, minimum=0, maximum=1)
                zone_save = gr.Button("Save zone")

            with gr.Tab("System & Privacy"):
                system_status = gr.Markdown()
                gr.Markdown(
                    "Frames arrive from this browser over the local laptop-to-GB10 connection. "
                    "The app retains event images and object references, not continuous video. "
                    "Gradio may create temporary upload/cache files; those live in the configured local temp directory.",
                    elem_classes=["lr-note"],
                )
                with gr.Row():
                    export_button = gr.Button("Export session")
                    export_file = gr.File(label="Session archive")
                delete_confirm = gr.Checkbox(label="I understand this deletes all saved LocalRecall memory")
                delete_button = gr.Button("Delete all memory", variant="stop")
                delete_result = gr.Markdown()

        def wrapped_analyze(before_image, after_image):
            try:
                return callbacks.analyze_pair(facade, before_image, after_image)
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def wrapped_ask(text):
            try:
                return callbacks.ask(facade, text or "")
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def wrapped_enroll(name, aliases, image):
            try:
                return callbacks.enroll_object(facade, name or "", aliases or "", image)
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def wrapped_load_zones():
            try:
                return callbacks.load_zones(facade)
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def wrapped_ingest(frame, session_id):
            try:
                return callbacks.ingest_browser_frame(facade, frame, session_id)
            except Exception as exc:  # noqa: BLE001 - display any ingress failure in the UI
                return f"Frame rejected: {exc}"

        def wrapped_review(event_id, decision):
            try:
                return callbacks.decide_event(facade, event_id, decision)
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def refresh_all():
            try:
                status, objects, gallery, pending = callbacks.refresh(facade)
                events = [
                    [event.id, event.object_id or "Unknown", event.event_type, event.from_zone_id, event.to_zone_id, event.confidence, event.accepted]
                    for event in facade.get_events(12)
                ]
                return status, status, objects, events, gallery, pending
            except Exception as exc:  # noqa: BLE001 - status polling must show unexpected backend errors
                message = f"Status unavailable: {exc}"
                return message, message, [], [], [], []

        def wrapped_watch(method):
            try:
                status = method(facade)
                return status
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def save_zone(name, slug, left, top, right, bottom):
            try:
                if hasattr(facade, "add_zone"):
                    record = facade.add_zone(name, slug, left, top, right, bottom)
                else:
                    raise RuntimeError("Zone editing is not available in this facade yet.")
                return f"Saved zone **{record.display_name}** (`{record.id}`)."
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def wrapped_export():
            try:
                return callbacks.export_session(facade)
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        def wrapped_delete(confirmed):
            try:
                return callbacks.delete_all_memory(facade, confirmed)
            except Exception as exc:
                raise gr.Error(str(exc)) from exc

        analyze_button.click(
            wrapped_analyze,
            inputs=[before, after],
            outputs=[event_summary, event_details, event_evidence],
            queue=True,
        )
        ask_button.click(wrapped_ask, inputs=[question], outputs=[answer, ask_evidence], queue=True)
        question.submit(wrapped_ask, inputs=[question], outputs=[answer, ask_evidence], queue=True)
        enroll_button.click(
            wrapped_enroll,
            inputs=[object_name, object_aliases, reference],
            outputs=[setup_result],
            queue=True,
        )
        zones_button.click(wrapped_load_zones, outputs=[zone_result], queue=True)
        zone_save.click(
            save_zone,
            inputs=[zone_name, zone_slug, x1, y1, x2, y2],
            outputs=[zone_result],
            queue=True,
        )
        browser_camera.stream(
            wrapped_ingest,
            inputs=[browser_camera, source_id],
            outputs=[ingest_status],
            stream_every=0.5,
            time_limit=60,
            queue=False,
        )
        watch_start.click(lambda: wrapped_watch(callbacks.start_watch)(), outputs=[status_line], queue=True)
        watch_stop.click(lambda: wrapped_watch(callbacks.stop_watch)(), outputs=[status_line], queue=True)
        approve.click(lambda event_id: wrapped_review(event_id, "approve"), inputs=[review_id], outputs=[review_result], queue=True)
        reject.click(lambda event_id: wrapped_review(event_id, "reject"), inputs=[review_id], outputs=[review_result], queue=True)
        export_button.click(wrapped_export, outputs=[export_file], queue=True)
        delete_button.click(wrapped_delete, inputs=[delete_confirm], outputs=[delete_result], queue=True)

        timer = gr.Timer(1.0)
        timer.tick(refresh_all, outputs=[status_line, system_status, object_table, event_table, memory_gallery, review_table], queue=False)
        demo.load(lambda: str(uuid4()), outputs=[source_id], queue=False)
        demo.load(refresh_all, outputs=[status_line, system_status, object_table, event_table, memory_gallery, review_table], queue=False)
        demo.queue(default_concurrency_limit=2, max_size=16)

    demo.allowed_paths = allowed_paths
    return demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LocalRecall Gradio interface")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="run deterministic fixture UI only")
    mode.add_argument("--backend", action="store_true", help="run the local Python backend facade")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mock:
        facade = MockFacade()
        port = args.port or 7861
        temp_allowed = str(facade._temp)
    else:
        settings = Settings(app_host=args.host, app_port=args.port or 7860, inference_mode="real")
        os.environ.setdefault("GRADIO_TEMP_DIR", str(Path(settings.gradio_temp_dir).resolve()))
        Path(os.environ["GRADIO_TEMP_DIR"]).mkdir(parents=True, exist_ok=True)
        facade = LocalRecallFacadeImpl(settings, mock=False)
        atexit.register(facade.close)
        port = args.port or settings.app_port
        temp_allowed = str(Path(settings.data_dir).resolve())
    app = create_app(facade, temp_allowed_path=temp_allowed)
    app.launch(
        server_name=args.host,
        server_port=port,
        share=False,
        show_error=True,
        allowed_paths=app.allowed_paths,
        show_api=False,
    )


if __name__ == "__main__":
    main()
