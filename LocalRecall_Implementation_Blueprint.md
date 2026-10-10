# LocalRecall: Private Event-Sourced Visual Memory

## ASUS Local AI Track Implementation Blueprint

**Target hardware:** ASUS Ascent GX10 / NVIDIA DGX Spark-class GB10 system

**Working environment:** Ubuntu 24.04 LTS, 4 TB storage, 128 GB unified memory, one GB10 Blackwell SoC

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

1. Cheap classical computer vision watches for motion.
2. The system keeps only a short in-memory ring buffer.
3. Once motion stops, it selects one clean BEFORE frame and one clean AFTER frame.
4. It creates a labeled comparison image containing zones and registered-object references.
5. `Qwen3.8-27B-NVFP4` analyzes that comparison locally and returns strict structured JSON.
6. A deterministic SQLite event log updates the object's last-known state.
7. The user asks a natural-language question and receives an evidence-backed answer.

This is deliberately scoped to be reliable in a hackathon:

- One fixed camera.
- Three to five enrolled objects.
- Three to four named zones.
- One meaningful object movement per event.
- No promise of general surveillance or unconstrained household understanding.
- No continuous raw-video retention.

---

# 2. Why this matches the Local AI track

The project should make four local-AI benefits visible during the demo:

1. **Privacy:** camera frames and memory remain on the GX10.
2. **Offline operation:** disconnect internet access and repeat the live demonstration.
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

1. Open the local web UI.
2. See a live camera view.
3. Configure or load three named zones.
4. Enroll at least three objects.
5. Start Watch Mode.
6. Move one object from one zone to another.
7. See an event appear automatically or through the manual fallback.
8. Ask, `Where are my keys?`
9. Receive the current zone plus BEFORE/AFTER evidence.
10. Disable external internet access and repeat the query.
11. Show that continuous raw video was not saved.

## 4.2 P1: strong judging version

Add only after P0 is reliable:

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

- Fixed USB webcam mounted overhead or at a stable 45-degree angle.
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
USB webcam or fixture video
        |
        v
Camera capture thread -----> in-memory ring buffer only
        |
        v
ROI-aware motion detector and state machine
        |
        +---- no meaningful scene change ----> discard
        |
        v
Clean stable BEFORE and AFTER frames
        |
        v
Composite builder
- BEFORE/AFTER labels
- named zone overlays
- enrolled-object reference strip
        |
        v
Local Qwen3.8-27B-NVFP4 endpoint
        |
        v
Strict event JSON
        |
        v
Pydantic validation + deterministic rules + one retry
        |
        +---- low confidence ----> review queue, no state mutation
        |
        v
SQLite append-only event log
        |
        +----> materialized object state
        +----> evidence thumbnails
        +----> metrics
        |
        v
FastAPI local web application
- live view
- object enrollment
- zone editor
- event timeline
- question answering
- privacy controls
- performance panel
```

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
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── camera.py
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
│   └── static/
│       ├── index.html
│       ├── app.js
│       ├── styles.css
│       └── assets/
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
    ├── test_api.py
    ├── test_event_pipeline_mock.py
    └── fixtures/
```

No framework should be added merely because it is fashionable. FastAPI, vanilla HTML/CSS/JavaScript, OpenCV, Pillow, Pydantic, HTTPX, and SQLite are sufficient.

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

# 10. Camera capture design

## 10.1 Capture thread

Implement one background thread that owns `cv2.VideoCapture`. Other components must not call the camera directly.

Default settings:

- resolution: 1280 x 720,
- requested FPS: 15,
- ring buffer: 60 frames,
- JPEG preview FPS: 5,
- motion-analysis size: 320 x 180.

Each frame record should contain:

- monotonic timestamp,
- UTC wall-clock timestamp,
- full-resolution BGR frame,
- downscaled grayscale frame,
- optional motion score.

If no camera is available, the exact same interface must read a looping fixture video. This is essential for development and automated testing.

## 10.2 Camera health

Expose:

- camera connected,
- source name,
- current frame age,
- capture FPS,
- dropped-frame count,
- current resolution.

If the frame is older than two seconds, show a visible camera error in the UI.

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
- moving confirmation: 3 consecutive frames,
- pre-event stable duration: 1.0 second,
- post-event stable duration: 1.2 seconds,
- cooldown: 1.5 seconds.

## 11.3 State machine

```text
NO_CAMERA
  -> STABLE

STABLE
  - continuously refresh the clean anchor frame
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

# 12. Zone editor

The zone editor should:

1. Freeze a current camera frame.
2. Let the user draw rectangular zones on a canvas.
3. Ask for a display name.
4. Save normalized coordinates.
5. Show zone labels over the live view.
6. Reject heavily overlapping zones unless explicitly confirmed.
7. Allow loading a default demo layout.

Use clear, high-contrast borders and large labels. The visual labels help both humans and the VLM.

---

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

# 19. FastAPI API contract

Minimum endpoints:

```text
GET    /api/health
GET    /api/status
GET    /api/live.mjpg
GET    /api/snapshot.jpg
POST   /api/watch/start
POST   /api/watch/stop
POST   /api/manual/before
POST   /api/manual/after
GET    /api/zones
POST   /api/zones
DELETE /api/zones/{zone_id}
GET    /api/objects
POST   /api/objects/enroll
DELETE /api/objects/{object_id}
GET    /api/events
GET    /api/events/{event_id}
POST   /api/events/{event_id}/accept
POST   /api/events/{event_id}/correct
POST   /api/query
GET    /api/metrics/summary
DELETE /api/memory
WS     /ws/status
```

`/api/status` should include:

```json
{
  "camera": "ok",
  "watch_state": "STABLE",
  "model": "ready",
  "offline_mode": true,
  "active_objects": 3,
  "active_zones": 3,
  "pending_reviews": 0,
  "last_event_id": 42,
  "last_model_latency_ms": 2840
}
```

---

# 20. Web interface

Use one polished single-page interface served by FastAPI.

## 20.1 Required screens or tabs

### Live

- live camera,
- zone overlays,
- Watch Mode toggle,
- large current state indicator,
- current motion score,
- latest event card,
- Manual Remember controls.

### Objects

- enrollment wizard,
- reference thumbnails,
- aliases,
- active/inactive toggle.

### Zones

- draw, name, edit, and delete zones,
- load demo layout.

### Memory

- chronological event timeline,
- BEFORE/AFTER evidence,
- confidence,
- accept/correct controls.

### Ask

- question input,
- evidence-backed answer,
- linked event cards,
- suggested example questions.

### Privacy and System

- model name,
- local endpoint status,
- offline mode,
- number of persisted event images,
- statement that continuous video is not retained,
- Delete All Memory button,
- inference latency summary,
- model-call count.

## 20.2 Design direction

Make it look like a finished appliance, not an admin dashboard:

- large readable typography,
- dark or neutral background,
- one strong accent color,
- clear status pills,
- evidence cards with obvious BEFORE and AFTER labels,
- very little developer jargon on the main screen.

Keep a hidden or secondary Technical Details drawer for the judges.

---

# 21. Privacy implementation

Privacy must be technically true, not just marketing copy.

Default behavior:

- continuous frames live only in a bounded RAM ring buffer,
- no continuous MP4 is written,
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

For the live judging demonstration, use a USB webcam and a local display so internet can be physically disconnected without breaking the app.

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
lsusb || true
v4l2-ctl --list-devices || true
ls -l /dev/video* 2>/dev/null || true
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
  --host 0.0.0.0 \
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
fastapi
uvicorn[standard]
pydantic
pydantic-settings
httpx
opencv-python-headless
pillow
numpy
python-multipart
jinja2
orjson
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
- API response.

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
app/static/
tests related to static assets or API rendering
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
- UI worktree: `app/static` only,
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

- scaffold FastAPI app,
- implement one manual BEFORE/AFTER flow,
- create composite,
- call VLM,
- validate event,
- insert into SQLite,
- answer `Where is X?`,
- show basic evidence page.

This is the highest-priority block.

### 2:15 to 4:00 - camera, zones, and automatic gate

- camera thread,
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

- show offline badge,
- move keys,
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
- [ ] Manual BEFORE/AFTER path works.
- [ ] At least one automatic movement path works.
- [ ] Accepted event updates SQLite state.
- [ ] `Where is X?` returns evidence.
- [ ] Internet can be disconnected after startup.
- [ ] No continuous video is stored.
- [ ] Delete All Memory works.
- [ ] Backup demo video exists.
- [ ] All three members can explain the system.

## Strong submission criteria

- [ ] Twenty-trial evaluation completed.
- [ ] Confidence review works.
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
