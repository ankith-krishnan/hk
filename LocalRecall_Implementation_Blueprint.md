# LocalRecall: Private Event-Sourced Visual Memory

## ASUS Local AI Track Implementation Blueprint

**Target hardware:** ASUS Ascent GX10 / NVIDIA DGX Spark-class GB10 system

**Working environment:** Headless Ubuntu 24.04 LTS DGX Spark (4 TB, 128 GB unified memory, one GB10). **No camera or display attached to Spark.** The laptop browser supplies images over a private local connection. **Important eligibility:** final judged submission must run on the organizer-provided ASUS Ascent GX10, not exclusively on the personal development Spark; verify model/container availability there before the demo.

**Team:** 3 people total

**Primary model:** `nvidia/Qwen3.8-27B-NVFP4`

**Project tagline:** **Ask your workspace where you left something, without sending a single frame to the cloud.**

---

# 1. Executive decision

Build a local visual-memory appliance that watches one bounded workspace, detects when a registered object is moved, stores a compact semantic event instead of continuous video, and answers questions such as:

- Where are my keys?
- What did I move most recently?
- What changed in the last ten minutes?
- Show me the evidence for where my wallet was last seen.

The winning technical idea is not continuous video captioning. It is **event-triggered semantic memory**:

1. Cheap classical computer vision watches for motion **in browser-supplied frames**; manual image-pair analysis works even without streaming.
2. The system keeps only a short in-memory ring buffer.
3. Once motion stops, it selects one clean BEFORE frame and one clean AFTER frame.
4. It creates a labeled comparison image containing zones and registered-object references.
5. `Qwen3.8-27B-NVFP4` analyzes that comparison locally and returns strict structured JSON.
6. A deterministic SQLite event log updates the object's last-known state.
7. The user asks a natural-language question and receives an evidence-backed answer.

This is deliberately scoped to be reliable in a hackathon:

- One fixed laptop webcam (or a USB camera attached to the laptop, never the headless Spark); manual uploads require no camera at all.
- Three to five enrolled objects.
- Three to four named zones.
- One meaningful object movement per event.
- No promise of general surveillance or unconstrained household understanding.
- No continuous raw-video retention.

---

# 2. Why this matches the Local AI track

The project should make four local-AI benefits visible during the demo:

1. **Privacy:** frames travel only between the presenter laptop and the local Spark through a protected SSH/LAN connection; inference and persistent memory stay on the GX10. Do not incorrectly claim the browser camera originates on the Spark.
2. **Offline operation:** show that no outside-WAN or cloud model connection is needed while KEEPING the laptop-to-Spark SSH/LAN connection active. Disconnecting the LAN itself would prevent headless browser access.
3. **Low operational cost:** no per-frame cloud API calls and no cloud video storage.
4. **Responsiveness and personalization:** objects, aliases, zones, and memories are specific to one user and one workspace.

The product should never look like a generic chat wrapper. The live camera, automatic event detection, evidence thumbnails, local database, privacy controls, and offline badge are the product.

---

# 3. Model strategy

## 3.1 Primary model

Use `nvidia/Qwen3.8-27B-NVFP4` as the only foundation model in the MVP.

Use it for:

- BEFORE/AFTER visual comparison.
- Registered-object identification.
- Zone-change extraction.
- Optional general natural-language summaries over database records.

Do not use it continuously on video. Invoke it only after the classical motion gate identifies a completed scene change.

## 3.2 Why NVFP4 matters

The checkpoint is already downloaded and is designed for Blackwell-class hardware. It uses mixed NVFP4/FP8 quantization. The lower weight footprint leaves substantial unified-memory headroom for the camera service, web app, image buffers, KV cache, and database.

The team should explicitly show the model name and local runtime in the technical slide and system status panel. Do not claim that every operation in the model is FP4; call it a mixed NVFP4/FP8 checkpoint.

## 3.3 Models intentionally excluded from the MVP

- `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16`: text-only and redundant for this project.
- `Alpamayo-1.5-10B`: visually capable but specialized for autonomous-driving scenes rather than desk-scale object memory.
- `Cosmos3-Nano`: powerful omnimodal world model, but its serving stack and generation capabilities are unnecessary for the MVP and increase risk.

Keep these files untouched. Do not delete or move their caches.

## 3.4 Runtime order

1. First choice: Spark-compatible vLLM container and an OpenAI-compatible local endpoint.
2. First fallback: SGLang Spark-compatible container with the same model.
3. Last-resort fallback: download one smaller, known-good VLM and preserve the same local API abstraction.

The application must depend on a small `VLMClient` interface so the runtime can be changed without rewriting the product.

## 3.5 Critical early validation gate

Before building the full app, prove all of the following:

1. The model loads on the single GB10.
2. A text request succeeds.
3. A one-image request succeeds.
4. A two-image request or one composite-image request succeeds.
5. The response can be constrained to parseable JSON.
6. The same request succeeds with Hugging Face offline mode enabled.

If image input does not work through vLLM after 60 to 90 minutes of focused debugging, switch to SGLang. Do not spend half the hackathon patching the inference engine.

---

# 4. Product scope

## 4.1 P0: mandatory demo path

The project is not considered viable until this entire sequence works:

1. Start Gradio on the headless Spark and reach it in the presenter laptop browser via SSH `-L` tunnel.
2. Use TWO separate browser `gr.Image` inputs (webcam snapshots or file uploads) to provide BEFORE and AFTER scenes; **no continuous stream required**.
3. Configure/load three named zones and enroll three objects.
4. Submit the image pair to the local Qwen model and see an evidence-backed event.
5. Ask `Where are my keys?` and receive the current zone plus BEFORE/AFTER evidence.
6. Disable only external internet (maintain the LAN/SSH connection) and repeat the query.
7. Show that the application does not intentionally persist continuous video, disclose Gradio temporary-file retention, and demonstrate memory deletion.

The automated browser-camera Watch Mode is a P1 enhancement; it must NEVER block P0.

## 4.2 P1: strong judging version

Add only after P0 is reliable:

- Stream ~2 fps from the presenter laptop webcam into `BrowserPushSource` using Gradio `.stream`, then drive the same event pipeline through OpenCV.
- Low-confidence review and one-click correction.
- Recent-event timeline.
- Queries such as `What changed in the last five minutes?`
- Measured inference latency and event accuracy.
- Privacy page with retention controls and Delete All Memory.
- A recorded backup demo.

## 4.3 P2: stretch goals

Do not begin these before the final demo is stable:

- Voice input or speech output.
- Automatic discovery of unknown objects.
- Multi-camera memory.
- Person identity.
- Long-form video summaries.
- Cosmos integration.
- Fine-tuning.
- Agent frameworks.
- Continuous VLM video inference.

---

# 5. Reliable physical demo setup

Use a controlled tabletop, not a general room.

Recommended setup:

- Presenter laptop webcam (or USB webcam plugged into the LAPTOP) fixed overhead/at 45 degrees. NO camera attaches to the Spark; screenshots/video uploads also work.
- 720p or 1080p capture, but process a smaller frame for motion detection.
- Stable lighting with no window glare.
- Three visibly distinct objects, for example:
  - keys,
  - red mug,
  - black wallet,
  - yellow toy,
  - blue notebook.
- Three or four physically clear destination zones:
  - LEFT TRAY,
  - CENTER MAT,
  - RIGHT TRAY,
  - SHELF.
- Put large printed labels such as A, B, and C in the physical scene if possible.

Avoid transparent objects, nearly identical items, reflective metal under glare, and closed drawers in the core demo. The system should not claim to know an object's hidden destination if the placement was not visible.

---

# 6. End-to-end architecture

```text
PRESENTER LAPTOP (webcam, Chrome/Firefox browser)
  |  Manual mode: gr.Image BEFORE + AFTER (snapshots OR uploads)
  |  Optional Watch: gr.Image(sources=["webcam"], streaming=True)
  |  Client webcam permission; camera never lives on Spark
  v
SSH local port forwarding: http://127.0.0.1:7860 (browser-side URL)
  |  local network only, no third-party tunnel
  v
HEADLESS DGX SPARK (Gradio Blocks Python process, 127.0.0.1:7860)
  |  facade.ingest_frame(RGB, source_id) --> BrowserPushSource RAM ring
  |  facade.analyze_pair(before_rgb, after_rgb) --> manual P0
  |  FixtureSource --> same backend pipeline
  v
Optional OpenCV motion gate (for streamed Watch mode only)
  |
  v
BEFORE / AFTER stable RGB frames
  |
  v
Composite image: zones, object references, BEFORE/AFTER labels
  |
  v
Qwen3.8-27B-NVFP4 local endpoint (127.0.0.1:8000)
  |
  v
Strict event JSON --> Pydantic validation --> review policy
  |
  v
SQLite event log, materialized object state, event evidence
  |
  v
Gradio Watch / Memory / Ask / Setup / System & Privacy
```

The browser laptop is a capture **client**, not a cloud inference provider. The Spark performs all model inference and data storage. Streaming samples are not sent to Qwen individually. A manual image pair and a completed motion event must converge on the same `analyze_pair`/event pipeline. A browser tab closing can interrupt live capture without corrupting memory.

---

# 7. Repository layout

Use a single Python repository with no mandatory Node.js build step.

```text
localrecall/
├── AGENTS.md
├── README.md
├── STATUS.md
├── RUNBOOK.md
├── DEMO_SCRIPT.md
├── ARCHITECTURE.md
├── Makefile
├── pyproject.toml
├── .env.example
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── facade.py
│   ├── contracts.py
│   ├── config.py
│   ├── schemas.py
│   ├── camera.py               # BrowserPushSource / FixtureSource (no /dev/video)
│   ├── frame_source.py         # frame ingress/lease/health
│   ├── motion.py
│   ├── zones.py
│   ├── composite.py
│   ├── vlm_client.py
│   ├── event_analyzer.py
│   ├── memory_store.py
│   ├── query_service.py
│   ├── telemetry.py
│   ├── privacy.py
│   ├── demo_mode.py
│   ├── prompts/
│   │   ├── event_extractor.txt
│   │   ├── event_repair.txt
│   │   └── query_answer.txt
│   └── ui/
│       ├── __init__.py
│       ├── app.py
│       ├── callbacks.py
│       ├── transforms.py
│       └── mock_facade.py
├── data/
│   ├── .gitkeep
│   ├── objects/
│   ├── events/
│   ├── fixtures/
│   └── localrecall.db
├── scripts/
│   ├── preflight.sh
│   ├── start_vllm.sh
│   ├── stop_vllm.sh
│   ├── wait_for_vllm.sh
│   ├── smoke_text.py
│   ├── smoke_vision.py
│   ├── start_app.sh
│   ├── make_fixture_video.py
│   ├── run_eval.py
│   ├── export_demo_bundle.sh
│   └── check_offline.sh
└── tests/
    ├── test_motion.py
    ├── test_schemas.py
    ├── test_memory_store.py
    ├── test_query_service.py
    ├── test_composite.py
    ├── test_facade.py
    ├── test_browser_frame_ingest.py
    ├── test_ui_contract.py
    ├── test_event_pipeline_mock.py
    └── fixtures/
```

Keep the stack small: Gradio Blocks, OpenCV, Pillow, Pydantic, HTTPX (only for the local VLM endpoint), NumPy, and SQLite. No additional REST web framework, frontend build tool, or WebSocket stack is necessary.

---

# 8. Data contracts

## 8.1 Registered object

```json
{
  "id": "keys",
  "display_name": "Keys",
  "aliases": ["key", "car keys", "house keys"],
  "reference_image_path": "data/objects/keys/reference.jpg",
  "active": true
}
```

Object IDs must be lowercase slugs and immutable after creation.

## 8.2 Zone

Store coordinates normalized to the camera image size.

```json
{
  "id": "left_tray",
  "display_name": "Left Tray",
  "polygon": [
    [0.03, 0.12],
    [0.31, 0.12],
    [0.31, 0.82],
    [0.03, 0.82]
  ]
}
```

Rectangles are sufficient for the MVP, but use a polygon-compatible schema.

## 8.3 VLM event result

```json
{
  "event_type": "move",
  "object_id": "keys",
  "from_zone_id": "left_tray",
  "to_zone_id": "right_tray",
  "confidence": 0.91,
  "visible_evidence": [
    "The key ring is visible in the left tray in BEFORE.",
    "The same key ring is visible in the right tray in AFTER."
  ],
  "uncertainty_reason": null
}
```

Allowed `event_type` values:

- `move`
- `appear`
- `disappear`
- `no_change`
- `uncertain`

The model may only return an `object_id` and zone IDs supplied in the prompt. Unknown values are invalid.

## 8.4 Event record

```json
{
  "id": 42,
  "started_at": "2026-10-10T18:31:11.251Z",
  "ended_at": "2026-10-10T18:31:15.803Z",
  "event_type": "move",
  "object_id": "keys",
  "from_zone_id": "left_tray",
  "to_zone_id": "right_tray",
  "confidence": 0.91,
  "accepted": true,
  "user_corrected": false,
  "pre_image_path": "data/events/42_before.jpg",
  "post_image_path": "data/events/42_after.jpg",
  "composite_path": "data/events/42_composite.jpg",
  "model_name": "nvidia/Qwen3.8-27B-NVFP4",
  "prompt_version": "event-v1",
  "model_latency_ms": 2840,
  "raw_response_json": {}
}
```

---

# 9. SQLite schema

Use SQLite in WAL mode. All event writes and state updates must happen in one transaction.

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS objects (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    reference_image_path TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS zones (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    polygon_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    object_id TEXT,
    from_zone_id TEXT,
    to_zone_id TEXT,
    confidence REAL NOT NULL,
    accepted INTEGER NOT NULL DEFAULT 0,
    user_corrected INTEGER NOT NULL DEFAULT 0,
    visible_evidence_json TEXT NOT NULL DEFAULT '[]',
    uncertainty_reason TEXT,
    pre_image_path TEXT,
    post_image_path TEXT,
    composite_path TEXT,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_latency_ms INTEGER,
    raw_response_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(object_id) REFERENCES objects(id),
    FOREIGN KEY(from_zone_id) REFERENCES zones(id),
    FOREIGN KEY(to_zone_id) REFERENCES zones(id)
);

CREATE TABLE IF NOT EXISTS object_state (
    object_id TEXT PRIMARY KEY,
    zone_id TEXT,
    last_event_id INTEGER,
    confidence REAL NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(object_id) REFERENCES objects(id),
    FOREIGN KEY(zone_id) REFERENCES zones(id),
    FOREIGN KEY(last_event_id) REFERENCES events(id)
);

CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    referenced_event_ids_json TEXT NOT NULL DEFAULT '[]',
    latency_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    labels_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

The event log is the historical source of truth. `object_state` is a materialized current-state table and must be rebuildable from accepted events.

---

# 10. Headless camera transport and frame-source design

## 10.1 Source contract

The Spark is **headless**: do NOT search for `/dev/video*` or treat absence of `cv2.VideoCapture(0)` as a failure. The backend consumes validated RGB NumPy arrays, not V4L2 devices.

Implement these source types behind one `FrameSource` abstraction:

1. `ManualPairSource`: two browser-provided still images (`gr.Image(sources=["webcam", "upload"], streaming=False, type="numpy")`) handed to `facade.analyze_pair(before, after)`. **P0 and guaranteed fallback.**
2. `BrowserPushSource`: a single Gradio browser webcam input `gr.Image(sources=["webcam"], streaming=True, type="numpy")` feeds `facade.ingest_frame(frame, source_id)` at about 2 frames/second. Optional automatic Watch Mode, P1.
3. `FixtureSource`: a known image pair or uploaded video FILE decoded locally (`cv2.VideoCapture(path)`, never device index). Automated tests and fallback.

Do not start VLM inference from a `.stream()` callback. Ingest only validates, downsamples, copies to a bounded ring buffer, timestamps receipt, and returns a cheap receipt/health string. The motion worker runs asynchronously against ring-buffer samples. Stream callback must complete quickly enough to sustain the sampling rate.

## 10.2 Browser streaming (only after manual MVP)

The frontend uses:

```python
webcam_stream = gr.Image(sources=["webcam"], streaming=True, type="numpy")
webcam_stream.stream(
    fn=callbacks.ingest_browser_frame,
    inputs=[webcam_stream, browser_source_id],  # a per-session gr.State token
    outputs=[ingest_status],
    stream_every=0.5,
    time_limit=60,
    queue=False,
)
```

**Keep two separate non-streaming image inputs for manual BEFORE/AFTER capture or upload.** Gradio input image streaming is webcam-only; do not combine streaming=True with `sources=["webcam", "upload"]`. Webcam preview is rendered by the browser camera input itself. A `gr.Timer` refreshes status, event counts, evidence, and memory (not the live browser source component).

Use browser-side localhost for secure camera permission:

```bash
# On the Spark:
python -m app.ui.app --backend --port 7860

# On the PRESENTING LAPTOP, not on the Spark:
ssh -N -L 7860:127.0.0.1:7860 <spark-user>@<spark-lan-ip>

# In a browser ON THAT LAPTOP:
# http://127.0.0.1:7860
```

Browser `getUserMedia()` requires HTTPS or a trustworthy origin such as localhost. Plain `http://<spark-ip>:7860` should NOT be relied upon for webcam access, even on a private LAN. If using a phone browser, use a properly secured HTTPS origin or instead take photos and upload them from the laptop; do not add a public Gradio share link.

## 10.3 Frame validation, motion, disconnects

- Accept only nonempty uint8 RGB HxWx3 arrays. Reject >1920x1080 or a strict decoded-pixel limit, normalize to a consistent geometry, and use 640x360/960x540 for the motion pipeline. Retain bounded evidence-quality frames temporarily in RAM only.
- Stamp time on server reception using a monotonic clock. Use elapsed times, not frame-count thresholds calibrated for 15fps, because browser capture defaults to ~2fps and may be irregular. **Detect persistent zone change between stable snapshots, not just motion across consecutive frames**: a hand may fully move an object between two 0.5s samples. Preserve the last clean anchor until the scene-change candidate is resolved.
- Hold at most 60 recent frames in a bounded RAM ring buffer (at 2fps, about 30 seconds of samples); drop old frames rather than enqueue unbounded work.
- Track source ID, frames received, ingest FPS, dropped frames, seconds since last receipt, and detection mode. Only one browser camera may be the active producer; reject interleaving a second session unless a lease expires or user explicitly selects it.
- If no frames arrive for 4 seconds, mark source disconnected and pause automatic Watch Mode; maintain manual uploads, database queries, and events.
- Never assume a laptop browser will keep streaming after its tab closes or sleeps; show explicit Camera Paused/Disconnected badges.
- Calibrate orientation: browser mirrored selfie-camera preview can invert Left and Right zones. Use a non-mirrored camera if available, or set zones based on the actual image entering the backend. Do a visible A/B/C zone test.
- User-uploaded videos are stored temporarily for decoding, not retained as continuous raw video. Gradio may create transient cache files for webcam frames/uploads: configure a dedicated temp area, log its real size, clear it on schedule/stop, and never claim zero temporary bytes without measurement.

## 10.4 Offline demonstration definition

All VLM inference happens on `127.0.0.1:8000` and all SQLite persistence on Spark. During the demo, keep the local laptop-to-Spark link active; external WAN/cloud service access may be unavailable. If you disable the ONLY network carrying SSH to the Spark, the browser demo will disconnect. Use a local-only wired/Ethernet or functioning LAN, and demonstrate no outside model endpoint rather than unplugging the critical connection. See `HEADLESS_CAMERA_RUNBOOK.md`.

---

# 11. Motion gate and event state machine

The motion gate should be intentionally simple and configurable.

## 11.1 Preprocessing

For each analysis frame:

1. Downscale to 320 x 180.
2. Convert to grayscale.
3. Apply a small Gaussian blur.
4. Normalize moderate global brightness changes if needed.
5. Restrict analysis to the union of configured zones when zones exist.

## 11.2 Motion score

Start with frame differencing:

1. `absdiff(previous_gray, current_gray)`
2. threshold the difference image,
3. morphological open and close,
4. compute changed-pixel fraction inside the region of interest.

Store both:

- total motion score,
- per-zone change score.

Do not hard-code final thresholds. Provide defaults and a calibration page.

Suggested starting values:

- stable threshold: 0.008,
- moving threshold: 0.025,
- moving confirmation: approximately 2 browser samples initially (timestamp-driven; tune to 2fps),
- pre-event stable duration: 1.0 second,
- post-event stable duration: 1.2 seconds,
- cooldown: 1.5 seconds.

## 11.3 State machine

```text
NO_CAMERA
  -> STABLE

STABLE
  - preserve the last clean anchor until a candidate change is resolved; refresh only when scene still matches the anchor
  - if motion exceeds threshold for N frames -> MOVING

MOVING
  - keep ring-buffer evidence
  - if motion falls below stable threshold -> SETTLING

SETTLING
  - if motion resumes -> MOVING
  - if stable duration reached -> CANDIDATE

CANDIDATE
  - choose BEFORE anchor
  - create AFTER as the median or sharpest of recent stable frames
  - compute per-zone scene-change scores
  - if no meaningful zone changed -> discard and return to STABLE
  - otherwise enqueue VLM analysis and enter COOLDOWN

COOLDOWN
  - ignore immediate duplicate events
  - after cooldown -> STABLE
```

The analysis queue should have a maximum length of one or two. If an event is already being analyzed, merge or discard duplicate candidates rather than creating a backlog.

## 11.4 Manual fallback

The UI must include a prominent **Manual Remember** mode:

1. Click `Capture BEFORE`.
2. Move an object.
3. Click `Capture AFTER and Analyze`.

Also add a keyboard shortcut. This fallback uses the same composite, inference, validation, storage, and query pipeline. It ensures the demo survives motion-threshold problems.

---

# 12. Zone configuration (Gradio-friendly)

For the P0 demo, provide a **Load Demo Zones** button for three rectangular workspace areas. Display readable zone outlines and labels on the backend-generated live preview.

The Setup tab may accept zone names and normalized rectangle coordinates (`x1, y1, x2, y2`) through ordinary Gradio text/number controls. Validate coordinate ranges and reject heavily overlapping zones unless explicitly confirmed. A browser drag-to-draw canvas is optional P2 scope, not a requirement for the hackathon demo.

# 13. Object enrollment

Object enrollment flow:

1. Ask the user to place one object in the center enrollment zone.
2. Capture a clean image.
3. Let the user draw or confirm a crop around the object.
4. Enter display name and aliases.
5. Save a 256 x 256 reference image.
6. Show a test prompt: `Can the local model match this reference to the current scene?`

For the MVP, reference images are optional hints, not learned embeddings. The composite builder places the enrolled references in a labeled strip below the BEFORE/AFTER comparison.

Limit the registry to five active objects for the live demo. More objects create unnecessary visual and prompt ambiguity.

---

# 14. Composite image design

Send one carefully constructed image to the VLM rather than raw video.

Recommended layout:

```text
+---------------------------+---------------------------+
| BEFORE                    | AFTER                     |
| zone overlays             | zone overlays             |
| timestamp                 | timestamp                 |
+-------------------------------------------------------+
| REGISTERED OBJECT REFERENCES                         |
| [keys] [wallet] [mug] [notebook]                    |
+-------------------------------------------------------+
| Allowed zones: left_tray, center_mat, right_tray     |
+-------------------------------------------------------+
```

Implementation requirements:

- Resize BEFORE and AFTER consistently.
- Draw zone IDs and display names.
- Draw a large BEFORE and AFTER heading.
- Include object reference crops with object IDs.
- Use a maximum total image size that keeps request latency reasonable.
- Save the exact composite used for inference as evidence.
- Compress to JPEG quality around 85, but keep text readable.

A single composite is easier to reason about, cache, inspect, and show to judges than an opaque video request.

---

# 15. Event-extraction prompt

Store the prompt in a versioned text file. A strong first version is:

```text
You are LocalRecallEventExtractor, a conservative visual change analyzer.

The supplied composite image contains:
- a BEFORE scene,
- an AFTER scene,
- labeled spatial zones,
- a strip of registered-object reference images.

Your task is to report at most one meaningful registered-object event.

Allowed object IDs:
{{OBJECT_IDS}}

Allowed zone IDs:
{{ZONE_IDS}}

Return exactly one JSON object with this schema:
{
  "event_type": "move|appear|disappear|no_change|uncertain",
  "object_id": "allowed object ID or null",
  "from_zone_id": "allowed zone ID, outside_view, or null",
  "to_zone_id": "allowed zone ID, outside_view, or null",
  "confidence": 0.0,
  "visible_evidence": ["short observation", "short observation"],
  "uncertainty_reason": "short reason or null"
}

Rules:
1. Compare only visible evidence in BEFORE and AFTER.
2. Do not invent an object, zone, or hidden destination.
3. Select object_id only from the supplied allowed IDs.
4. Select zone IDs only from the supplied allowed IDs or outside_view.
5. Use move only when the same registered object clearly changes location.
6. Use appear when the object is absent before and visible after.
7. Use disappear when the object is visible before and absent after.
8. Use no_change if a hand moved but no registered object changed location.
9. Use uncertain when evidence is ambiguous.
10. If more than one object moved, report the clearest one and mention ambiguity.
11. confidence must reflect visual certainty, not conversational confidence.
12. Output JSON only. Do not add Markdown or explanations.
```

Inference defaults:

- temperature: 0.0,
- top_p: 1.0,
- max_tokens: 512,
- thinking disabled if the runtime supports per-request thinking control,
- request timeout: 180 seconds.

---

# 16. Response validation

Never mutate memory directly from an unchecked model string.

Validation sequence:

1. Remove optional Markdown fences.
2. Parse JSON.
3. Validate against a Pydantic model.
4. Confirm object ID exists.
5. Confirm zones exist.
6. For `move`, require different FROM and TO values.
7. Clamp confidence into [0, 1] only if the rest is valid.
8. If invalid, retry once with the original response and a repair prompt.
9. If still invalid, create an `uncertain` event and do not update object state.

Suggested decision thresholds:

- confidence >= 0.70: auto-accept,
- 0.45 <= confidence < 0.70: review queue,
- confidence < 0.45: uncertain, no state update.

These thresholds must be configurable. Tune them using actual tests rather than intuition.

---

# 17. Memory semantics

The database, not the language model, owns memory.

Rules:

- Accepted `move` and `appear` events update current state.
- Accepted `disappear` sets the zone to `outside_view` or unknown.
- `no_change` never updates state.
- `uncertain` never updates state.
- A user correction creates an audit record and then rebuilds object state.
- If no accepted evidence exists, answer `I do not have a reliable observation yet.`
- Never answer a location based only on conversational context.

Answers should include:

- object display name,
- current zone display name,
- last observed time,
- confidence,
- event ID,
- evidence thumbnail.

---

# 18. Query service

Use a two-tier query system.

## 18.1 Deterministic fast path

Handle common questions without another model call:

- Where is X?
- When was X last moved?
- What moved most recently?
- List current object locations.
- Show event N.

Resolve object names through exact IDs, display names, aliases, and conservative fuzzy matching.

## 18.2 Local-model fallback

For broader questions:

- What changed in the last ten minutes?
- Did I move the wallet after the keys?
- Summarize today's object activity.

Retrieve only relevant database records, then send a compact text-only prompt to the same local Qwen endpoint.

The model must be instructed:

- answer only from supplied records,
- cite event IDs,
- say unknown when records are insufficient,
- never infer an unobserved location.

Do not implement a complex autonomous agent loop for the MVP.

---

# 19. In-process Python facade contract

The UI must never access camera, SQLite, or VLM internals directly. Use the single in-process `LocalRecallFacade` protocol from `app/contracts.py`, with concrete adapters in `app/facade.py`, and keep it stable once the UI worktree begins.

## Python facade: one shared contract

Gradio and backend communicate through direct Python calls, not a new HTTP API. Implement `app/facade.py` as the adapter to backend services and `app/contracts.py` for dataclasses/Pydantic schemas. Publish these methods before UI work begins:

```python
class LocalRecallFacade(Protocol):
    def get_status(self) -> SystemStatus: ...
    def get_latest_frame(self) -> np.ndarray | None: ...  # from browser ingestion or fixture
    def ingest_frame(self, frame: np.ndarray, source_id: str) -> dict: ...
    def analyze_pair(self, before: np.ndarray, after: np.ndarray) -> EventRecord: ...
    def get_objects(self) -> list[ObjectRecord]: ...
    def get_zones(self) -> list[ZoneRecord]: ...
    def get_events(self, limit: int = 50) -> list[EventRecord]: ...
    def start_watch(self) -> SystemStatus: ...
    def stop_watch(self) -> SystemStatus: ...
    def ask(self, question: str) -> QueryResult: ...
    def enroll_object(self, display_name: str, description: str, reference_image: np.ndarray) -> ObjectRecord: ...
    def load_demo_zones(self) -> list[ZoneRecord]: ...
    def approve_event(self, event_id: int) -> EventRecord: ...
    def reject_event(self, event_id: int) -> EventRecord: ...
    def get_health(self) -> dict: ...
    def export_session(self) -> Path: ...
    def delete_all_memory(self) -> None: ...
```

Implement both real and mock facades. The mock returns deterministic fixture records and must NOT open the camera, start vLLM, or connect to the model. The real facade owns a single backend-service instance. The real facade ingests RGB frames from browser streaming through a bounded `BrowserPushSource`. Only fixture/video-file decoder code may call `cv2.VideoCapture(path)`; never open `/dev/video*` on Spark. Manual `analyze_pair` works without any active webcam stream. Event history, object state, and privacy settings persist in SQLite, not `gr.State`. Synchronous facade calls may delegate to a worker; do not block Gradio's polling callbacks on model inference.

Use these application entrypoints:

```bash
python -m app.ui.app --mock --port 7861
python -m app.ui.app --backend --port 7860
```

The normal Gradio app binds only `127.0.0.1:7860` on the headless Spark. The presenter opens `http://127.0.0.1:7860` on the LAPTOP via `ssh -N -L 7860:127.0.0.1:7860 <user>@<spark-lan-ip>`, satisfying browser webcam secure-context requirements. Gradio sharing must remain disabled; no independent camera service is needed. The model endpoint binds only `127.0.0.1:8000`.

# 20. Gradio Blocks interface

Use `gr.Blocks` in `app/ui/app.py`; UI callbacks are implemented in `app/ui/callbacks.py` and formatting in `app/ui/transforms.py`. The required tabs are **Watch**, **Memory**, **Ask**, **Setup**, **System & Privacy**.

- **Watch:** browser-owned `gr.Image(sources=["webcam"], streaming=True)` for optional Watch Mode; independent non-streaming `gr.Image(sources=["webcam", "upload"])` for manual BEFORE and AFTER, Analyze button, connected/stale source status and evidence. Distinguish server-held frame from browser preview.
- **Memory:** `gr.Dataframe` for current state, timeline, review/approval controls, `gr.Gallery` of BEFORE/AFTER/composite images.
- **Ask:** `gr.Textbox`, Ask button, evidence-backed answer including event ID, image, and confidence.
- **Setup:** enroll one of three to five objects with a reference image; load default zones; numeric normalized rectangles are sufficient for the MVP (no drag canvas).
- **System & Privacy:** actual offline/model/camera status, latency, evidence retention, export, confirmation before delete.

Run the UI in mock mode on `localhost:7861` for your teammate, without starting model or camera. Run the integrated UI on `localhost:7860` with the real facade. A `gr.Timer` every 0.5-1.0 seconds refreshes only cheap health/events/evidence with `queue=False`, never the webcam input and never inference. The browser `.stream()` callback does ONLY frame ingestion. The manual Analyze button calls `facade.analyze_pair(before, after)` in a queued handler. Manual BEFORE/AFTER + Analyze executes as a queued click action. Do not use `gr.State` for event truth, and avoid custom JavaScript and remote assets.

Use a readable restrained appliance aesthetic, prominent offline/local indication, and clear BEFORE/AFTER evidence. A small secondary technical-details area should explain NVFP4, event-gated inference, SQLite memory, and uncertainty handling to judges.

# 21. Privacy implementation

Privacy must be technically true, not just marketing copy.

Default behavior:

- continuous application frames live only in a bounded RAM ring buffer,
- no continuous MP4 is written,
- Gradio may place transient webcam/upload image data in its temp cache. Use a dedicated `GRADIO_TEMP_DIR` when supported, configure pruning/deletion, measure actual temp use, and disclose this instead of falsely claiming zero transient frame files,
- only accepted or reviewable event images are persisted,
- all persisted images are listed in the UI,
- the user can delete all memory,
- no cloud API keys are required,
- model server is on localhost,
- analytics are local only.

Add environment variable:

```text
OFFLINE_MODE=1
```

When enabled:

- use `HF_HUB_OFFLINE=1`,
- use `TRANSFORMERS_OFFLINE=1`,
- reject non-local model base URLs,
- show an offline badge,
- log any attempted outbound URL as an error.

For live judging, show the laptop webcam streaming to the headless Spark via a PRIVATE SSH tunnel while WAN access is disabled or unnecessary; retain the LAN carrying SSH. If camera streaming is unreliable, switch to the mandatory pair-of-images upload/snapshot workflow. Never disable the only route to the headless server.

---

# 22. Runtime and startup plan

## 22.1 Host preflight

Codex should run and record:

```bash
uname -a
uname -m
cat /etc/os-release
nvidia-smi || true
free -h
df -h
docker --version
docker info >/tmp/docker-info.txt
hostname -I || true
ss -ltn 2>/dev/null | head -30 || true
# Headless Spark: no local webcam/monitor expected; not an error.
```

It must locate the existing model cache without redownloading or deleting anything.

## 22.2 Container

Use the current Spark-specific Qwen3.8 vLLM image:

```text
vllm/vllm-openai:qwen38
```

Use the local cached model handle:

```text
nvidia/Qwen3.8-27B-NVFP4
```

A reasonable starting launch command is below. Codex must validate flags against the image's `--help` output and adjust minimally if the image's entrypoint differs.

```bash
docker rm -f localrecall-vllm 2>/dev/null || true

docker run -d \
  --name localrecall-vllm \
  --gpus all \
  --ipc host \
  --network host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface/hub:/root/.cache/huggingface/hub" \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  vllm/vllm-openai:qwen38 \
  --model nvidia/Qwen3.8-27B-NVFP4 \
  --host 127.0.0.1 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --kv-cache-dtype fp8 \
  --gpu-memory-utilization 0.75 \
  --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --enable-chunked-prefill \
  --reasoning-parser qwen3
```

Do not add speculative decoding, custom kernels, tool calling, or an extreme context window until image inference is stable.

If the container entrypoint does not accept these flags directly, run `vllm serve` through an explicit shell entrypoint. The script must probe readiness through `/health` and `/v1/models`.

## 22.3 Application environment

Suggested Python dependencies:

```text
gradio
pydantic
pydantic-settings
httpx
opencv-python-headless
pillow
numpy
rapidfuzz
pytest
pytest-asyncio
```

Prefer Python's built-in `sqlite3` over a heavy ORM for this time-limited project.

---

# 23. Smoke tests

## 23.1 Text smoke test

- Request one short answer.
- Confirm HTTP 200.
- Record latency.

## 23.2 Image smoke test

Generate or capture a simple image, send it through the OpenAI-compatible multimodal message format, and ask for one visible fact.

## 23.3 Change-analysis smoke test

Create a synthetic composite with a colored object moved from a labeled left zone to a labeled right zone. Ask for the strict event schema.

Pass criteria:

- parseable JSON,
- correct object ID,
- correct zone transition,
- no extra prose.

## 23.4 Offline smoke test

Restart with offline environment variables and repeat. The test should fail loudly if the model cache is incomplete rather than silently using a network service.

---

# 24. Testing strategy

## 24.1 Unit tests

Test without a real model:

- motion-state transitions,
- stable frame selection,
- zone masks,
- composite dimensions and labels,
- JSON cleanup and validation,
- confidence thresholds,
- transactional event insertion,
- current-state rebuild,
- object alias resolution,
- deterministic location answers,
- privacy deletion.

## 24.2 Integration test with mock model

Run a tiny local mock OpenAI-compatible server that returns scripted JSON. Exercise:

- camera fixture,
- motion candidate,
- composite creation,
- model call,
- event insertion,
- query answer,
- facade result and Gradio callback output.

This lets the team develop the complete product while the real model server is loading or being debugged.

## 24.3 Real-model evaluation

Create at least 20 scripted trials:

- 3 to 5 objects,
- 3 zones,
- move events,
- no-change hand passes,
- appearance,
- disappearance,
- one deliberately ambiguous trial.

Record ground truth in a JSONL or CSV fixture.

Report only measured results:

- event detection precision,
- event detection recall,
- object identification accuracy,
- destination-zone accuracy,
- median model latency,
- 95th-percentile model latency,
- end-to-end event latency,
- false-positive count,
- persisted continuous-video bytes, expected zero.

Do not invent numbers for the pitch.

---

# 25. Feasibility gates and hard fallback rules

## Gate A: 60 to 90 minutes after start

Must have one successful local image request.

If not:

1. check model cache integrity,
2. inspect container logs,
3. try a one-image request rather than video,
4. remove optional flags,
5. try SGLang with the same checkpoint,
6. if still blocked, switch to a smaller known-good VLM.

## Gate B: roughly three hours after start

Must have manual BEFORE/AFTER to database to query working end to end.

If not:

- stop building automatic motion detection,
- stop UI polish,
- repair the single critical path.

## Gate C: Saturday evening

Must have a repeatable live demo and recorded backup.

If automatic detection is unreliable:

- use Manual Remember during judging,
- keep automatic mode as a visible beta feature,
- do not gamble the entire demo on threshold tuning.

## Gate D: final morning

No architectural rewrites. Only reliability fixes, documentation, metrics, and presentation.

---

# 26. Team operating model

The user is the technical architect and integration owner, not necessarily the presentation leader.

## Member 1: technical architect

Owns:

- model runtime,
- VLM client,
- event schema,
- database semantics,
- motion pipeline,
- final integration,
- difficult debugging.

## Member 2: product experience owner

Owns a bounded branch and only edits:

```text
app/ui/
tests/test_ui_contract.py
UI_HANDOFF.md and TASK_UI.md
```

Responsibilities:

- visual layout,
- Live page,
- timeline cards,
- Ask page,
- Privacy page,
- labels and copy,
- user testing.

This person can direct a Codex agent from a graphical window and review the browser output without knowing SSH.

## Member 3: evaluation and demo owner

Owns:

```text
scripts/run_eval.py
tests/fixtures/
DEMO_SCRIPT.md
README sections for results
Devpost copy and presentation notes
```

Responsibilities:

- enroll demo objects,
- define the 20-trial matrix,
- run and record results,
- catalog failures,
- create the backup video,
- make sure the pitch is understandable.

## Shared requirement

Every member must be able to explain:

- why the project is local,
- what the model does,
- what the database does,
- why continuous video is not stored,
- what happens when confidence is low.

Run two short teach-back sessions where each member explains the architecture without notes.

---

# 27. Git and Codex workflow for non-experts

Use worktrees so parallel Codex agents do not collide.

After the initial scaffold commit:

```bash
git worktree add ../localrecall-ui -b feature/ui
git worktree add ../localrecall-eval -b feature/eval
```

Ownership boundaries:

- main/core worktree: Python backend and integration,
- UI worktree: `app/ui/**` and `tests/test_ui_contract.py` only; facade/protocol changes must go through the core owner,
- evaluation worktree: fixtures, evaluation scripts, and docs only.

Each agent must:

1. read `AGENTS.md`,
2. write a short plan into its task file,
3. modify only owned paths,
4. run relevant tests,
5. commit with a descriptive message,
6. write a handoff summary.

The technical owner merges or cherry-picks. Friends do not need to use Git commands manually; Codex can execute them.

---

# 28. Hour-by-hour execution plan

## Saturday

### 12:00 to 12:45 - environment and model gate

- run preflight,
- locate model cache,
- pull or verify the Qwen3.8 Spark vLLM image,
- start model,
- pass text smoke test,
- pass image smoke test.

### 12:45 to 2:15 - manual end-to-end vertical slice

- scaffold Python facade and minimum Gradio Blocks app,
- implement one manual BEFORE/AFTER flow,
- create composite,
- call VLM,
- validate event,
- insert into SQLite,
- answer `Where is X?`,
- show basic evidence page.

This is the highest-priority block.

### 2:15 to 4:00 - camera, zones, and automatic gate

- BrowserPushSource ingest + disconnect health (NO camera thread),
- fixture-video fallback,
- zone editor or default zones,
- motion state machine,
- event queue,
- live status.

### 4:00 to 5:30 - enrollment and product UI

- object enrollment,
- reference strip,
- polished Live screen,
- Memory timeline,
- Ask interface.

### 5:30 to 7:00 - integration and real trials

- run real object moves,
- tune thresholds,
- fix VLM prompt,
- add confidence review,
- log latency.

### 7:00 to 8:30 - evaluation and privacy story

- run trial matrix,
- offline restart,
- verify no continuous video,
- add privacy/system page,
- start Devpost draft.

### 8:30 to 9:20 - demo hardening

- record backup video,
- rehearse three-minute pitch,
- fix only demo-blocking issues,
- capture screenshots.

### 9:20 to 9:45 - freeze and backup

- tag a known-good commit,
- export repository bundle,
- copy SQLite demo data and presentation assets,
- stop risky changes.

### By 10:00 - venue close

Leave with a bootable, recorded, known-good version.

## Sunday

### 9:00 to 10:00

- cold boot test,
- start model from scripts,
- run smoke test,
- run one complete demo.

### 10:00 to 11:30

- finish measured evaluation,
- finalize technical diagram,
- finalize pitch and Q&A answers.

### 11:30 to 12:30

- complete Devpost,
- upload backup video and screenshots,
- verify repository instructions.

### 12:30 to 1:00

- freeze submission,
- final table setup,
- all members rehearse.

Do not wait until the 1:30 PM deadline.

---

# 29. Three-minute pitch structure

## 0:00 to 0:25 - problem

`People forget where they put everyday objects. A cloud-connected camera can solve it, but it sends private video away and creates continuous cost.`

## 0:25 to 0:45 - solution

`LocalRecall is a private visual memory running entirely on the ASUS GX10. It stores semantic events rather than continuous video.`

## 0:45 to 1:35 - live demo

- show local-model status and local-only transport while WAN is unavailable,
- move keys using laptop webcam or show BEFORE/AFTER uploads,
- event appears,
- ask where the keys are,
- open evidence.

## 1:35 to 2:15 - technical differentiator

- motion gate avoids continuous VLM inference,
- Qwen3.8 NVFP4 compares only meaningful BEFORE/AFTER frames,
- SQLite owns factual memory,
- low-confidence events require review.

## 2:15 to 2:40 - measured result

Show real accuracy and latency numbers.

## 2:40 to 3:00 - impact

Mention accessibility, elder care, workshops, laboratories, and privacy-sensitive workplaces without claiming production readiness.

---

# 30. Acceptance criteria

## P0 ship criteria

- [ ] App starts from documented commands.
- [ ] Model runs locally on the GX10/Spark.
- [ ] Image inference works.
- [ ] Three objects can be enrolled.
- [ ] Three zones can be configured.
- [ ] Two browser-supplied images (webcam snapshots or upload) work end-to-end via `analyze_pair`.
- [ ] The same manual path works with no browser webcam and no server camera.
- [ ] Optional P1: browser-streamed automatic movement path works.
- [ ] Accepted event updates SQLite state.
- [ ] `Where is X?` returns evidence.
- [ ] WAN/cloud access can be disabled while local LAN/SSH to headless Spark stays active.
- [ ] No continuous application video is persisted; temporary Gradio cache is measured and cleanup is configured.
- [ ] Delete All Memory works.
- [ ] Backup demo video exists.
- [ ] All three members can explain the system.

## Strong submission criteria

- [ ] Twenty-trial evaluation completed.
- [ ] Confidence review works.
- [ ] Laptop SSH localhost tunnel, browser webcam permission, stale-stream recovery and upload-only fallback verified.
- [ ] Cold-start runbook verified.
- [ ] Technical architecture diagram ready.
- [ ] Devpost submitted before deadline.

---

# 31. Things Codex must not do

- Do not delete Hugging Face caches.
- Do not redownload models unless cache validation proves files are missing.
- Do not introduce any cloud API dependency.
- Do not make continuous video persistence the default.
- Do not start with React, Kubernetes, Redis, Kafka, or an agent framework.
- Do not fine-tune a model during the critical path.
- Do not silently replace the NVFP4 model.
- Do not use Cosmos, Alpamayo, or Nemotron without an explicit stretch-goal decision.
- Do not use `git reset --hard` on uncommitted team work.
- Do not claim tests passed without running them.
- Do not fabricate benchmark results.
- Do not expose the app to the public internet.
- Do not store secrets in the repository.

---

# 32. Final strategic advice

The impressive part is not using the largest model available. The impressive part is making a 27B multimodal NVFP4 model behave like a dependable local appliance through:

- sparse event-triggered inference,
- deterministic state management,
- evidence-backed answers,
- conservative uncertainty handling,
- privacy-by-design storage,
- a polished offline demonstration.

A reliable manual BEFORE/AFTER pipeline with excellent evidence is more valuable than a broken promise of universal real-time vision. Build the vertical slice first, then automate it.
