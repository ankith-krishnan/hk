# Master Prompt for Codex: Build LocalRecall

Use this master prompt from the root of the EXISTING `hk` Git repository on the Ubuntu 24.04 DGX Spark / ASUS GX10-class machine. Preserve the existing three planning documents and Git history; implement the application alongside them.

---

You are the principal implementation agent for a time-constrained local-AI hackathon project named **LocalRecall**.

Your job is to autonomously build, test, document, and harden a complete working application on the current machine. Work incrementally and keep a runnable vertical slice at all times. Do not merely write a plan. Inspect the machine and existing repository, implement the code in place, run tests, start services, exercise the Gradio UI and model endpoint, and record concrete results.

## Product objective

Build a private visual-memory appliance for a bounded tabletop workspace. It must:

1. Capture browser-camera frames from a laptop via Gradio, or use manual browser snapshots / uploaded image pairs / fixture video. The DGX Spark is headless and has NO attached camera.
2. Let the user define three to four named spatial zones.
3. Let the user enroll three to five named objects with reference images and aliases.
4. Detect the start and end of meaningful motion using cheap OpenCV processing.
5. Select one clean BEFORE frame and one clean AFTER frame.
6. Build one labeled composite image containing BEFORE, AFTER, zone overlays, and registered-object references.
7. Send that composite to the local model `nvidia/Qwen3.8-27B-NVFP4`.
8. Receive and validate strict structured JSON describing at most one object event.
9. Store the accepted event in SQLite and update deterministic current object state.
10. Answer questions such as `Where are my keys?` with event evidence.
11. Run without any cloud inference/API; retain no continuous application video, and explicitly manage any transient Gradio upload/cache files.
12. Provide a polished local web UI and a manual BEFORE/AFTER fallback.

The final live demonstration must work without external internet while maintaining a LOCAL network link (e.g. LAN or directly connected Ethernet) between the presenting laptop/browser and Spark. Never disconnect the SSH session or LAN that carries the Gradio stream.

## Current machine and model assumptions

- Ubuntu 24.04 LTS.
- NVIDIA GB10 Blackwell-class integrated GPU/CPU.
- 128 GB unified memory.
- 4 TB local storage.
- Docker and NVIDIA Container Toolkit should be available.
- CRITICAL: the DGX Spark is headless, with NO physically attached camera or display. A presenter laptop provides the camera in its browser. Do NOT attempt `cv2.VideoCapture(0)` on the Spark or require `/dev/video*`.
- Gradio binds to `127.0.0.1:7860`; the presenter laptop opens `http://127.0.0.1:7860` via SSH port forwarding. Browser webcam access depends on a secure context (localhost or HTTPS) and explicit permission.
- The Hugging Face cache already contains:
  - `nvidia/Qwen3.8-27B-NVFP4`
  - `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16`
  - `nvidia/Alpamayo-1.5-10B`
  - `nvidia/Cosmos3-Nano`
- Use only `nvidia/Qwen3.8-27B-NVFP4` in the MVP.
- The preferred Spark-specific image is `vllm/vllm-openai:qwen38`.
- The **judged** Local AI submission must run on an organizer-provided **ASUS Ascent GX10**, as required by the track. Personal DGX Spark development is preparation, not a substitute. Verify Qwen checkpoint/container availability and transfer time on the actual ASUS machine as soon as it is checked out.
- The model is a mixed NVFP4/FP8 multimodal checkpoint. Do not describe it as pure FP4.
- Its image path must be proven with a smoke test before the rest of the application depends on it.

Do not delete, relocate, or overwrite any existing model cache.

## Operating principles

1. Make progress without repeatedly asking the user questions. Resolve ordinary implementation choices yourself.
2. Ask only before a destructive action, privilege escalation with broad impact, or an irreversible change.
3. Prefer a small dependable implementation over a broad fragile one.
4. Keep all model access behind a `VLMClient` abstraction.
5. Use mock inference so application development can continue while the real model loads.
6. Commit after each completed milestone.
7. Update `STATUS.md` after every milestone with:
   - completed work,
   - commands run,
   - tests and results,
   - current blockers,
   - next action.
8. Never claim a test passed without running it.
9. Never fabricate accuracy, throughput, or latency results.
10. Preserve a known-good tagged commit before risky changes.

## Non-negotiable technical constraints

- Backend: Python 3.11 or 3.12, OpenCV, Pydantic, SQLite, and a stable in-process Python facade.
- Frontend: Python Gradio Blocks. No FastAPI/HTTP application API, WebSockets, React, HTML/JavaScript frontend, or Node build required.
- Gradio imports the facade only; backend internals stay private.
- Gradio and app dependencies must be pinned to compatible tested versions in `pyproject.toml`.
- Vision gate: OpenCV and NumPy, applied to frames received via browser upload or fixture. Never treat server-local camera hardware as required.
- Image composition: Pillow or OpenCV.
- Validation: Pydantic.
- Model client: HTTPX against an OpenAI-compatible localhost endpoint.
- Storage: Python `sqlite3`, WAL mode, foreign keys enabled.
- Tests: pytest.
- No cloud APIs.
- No Redis, Kafka, Kubernetes, or external database.
- No continuous video files by default.
- No fine-tuning.
- No autonomous agent framework in the application.
- Do not add Nemotron, Cosmos, or Alpamayo to the critical path.

## Required repository structure

Create this structure, adapting only when necessary:

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
│   ├── camera.py               # BrowserPushSource/FixtureSource, NOT V4L2 capture
│   ├── frame_source.py         # Source abstraction and stale-frame/lease logic
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

## Phase 0: inspect and document the environment

Immediately run the following or safe equivalents:

```bash
pwd
uname -a
uname -m
cat /etc/os-release
python3 --version
nvidia-smi || true
free -h
df -h
docker --version
docker info >/tmp/localrecall-docker-info.txt
hostname -I || true
ss -ltn 2>/dev/null | head -30 || true
# NO local webcam or /dev/video* is expected on this headless Spark.
find "$HOME/.cache/huggingface/hub" -maxdepth 3 -type d -name '*Qwen3.8-27B-NVFP4*' 2>/dev/null || true
docker image ls
```

Write the result and interpretation into `STATUS.md` under `Environment Preflight`.

Do not dump secrets into tracked files.

Use the existing Git repository and preserve its commits. Commit the scaffold and new implementation files; never overwrite the planning documents with generated placeholders.

## Phase 1: prove the model runtime

### 1A. Locate cache and image

Verify that the Qwen checkpoint is complete. Do not redownload unless required files are missing.

Pull `vllm/vllm-openai:qwen38` only if it is not already available.

Inspect its entrypoint and `--help` output before finalizing the launch script.

### 1B. Create a conservative start script

Start from this configuration, but validate every flag against the actual image:

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

If the image's entrypoint requires `--model` in a different form, correct the script minimally. If the model cannot start with offline variables because the cache is incomplete, allow one online completion step, then retest offline.

Do not add speculative decoding, tool calling, MTP tuning, custom CUDA builds, or huge context lengths during this phase.

### 1C. Implement readiness checks

`wait_for_vllm.sh` must:

- poll `/health`,
- poll `/v1/models`,
- time out cleanly,
- print the last container logs on failure.

### 1D. Text smoke test

Implement `scripts/smoke_text.py`. It must:

- call localhost only,
- request a short deterministic answer,
- print HTTP status and latency,
- fail with a nonzero code on malformed output.

### 1E. Vision smoke test

Implement `scripts/smoke_vision.py` using an OpenAI-compatible multimodal request. It should first generate a synthetic image with two labeled zones and one distinctive object, then ask the model to describe the visible object.

Then generate one composite image with the object moved from LEFT to RIGHT and ask for strict JSON.

Required pass conditions:

- HTTP 200,
- image accepted,
- parseable JSON after conservative cleanup,
- correct movement direction or at least correct visible zones in the initial test.

Save the request image and raw response under `data/fixtures/smoke/`.

### 1F. Runtime fallback

If vLLM text works but image requests fail:

1. simplify to one image and a short prompt,
2. remove optional serving flags,
3. inspect the model processor/config inside the container,
4. verify the request content format,
5. try the current Spark-compatible SGLang path using the same cache and model.

Do not spend more than 90 focused minutes on one runtime. Preserve `VLMClient` compatibility.

After Phase 1, commit with a message similar to:

```text
feat: validate local Qwen3.8 NVFP4 text and vision inference
```

Update `STATUS.md` with real latency and any caveats.

## Phase 2: build a complete manual vertical slice

Do this before automatic motion detection.

### 2A. Configuration

Create a Pydantic settings class supporting at least:

```text
APP_HOST=127.0.0.1
APP_PORT=7860
DATA_DIR=./data
DATABASE_PATH=./data/localrecall.db
VLM_BASE_URL=http://127.0.0.1:8000/v1
VLM_MODEL=nvidia/Qwen3.8-27B-NVFP4
VLM_TIMEOUT_SECONDS=180
OFFLINE_MODE=1
FRAME_SOURCE=browser
BROWSER_STREAM_INTERVAL_SEC=0.5
BROWSER_MAX_WIDTH=1280
BROWSER_SOURCE_STALE_SECONDS=4
FIXTURE_VIDEO_PATH=
AUTO_ACCEPT_CONFIDENCE=0.70
REVIEW_CONFIDENCE=0.45
```

Reject non-local VLM URLs when `OFFLINE_MODE=1`.

### 2B. Schemas

Implement Pydantic models for:

- ObjectRecord,
- ZoneRecord,
- VLMEventResult,
- EventRecord,
- ObjectState,
- QueryRequest,
- QueryResponse,
- SystemStatus.

Allowed event types:

```text
move, appear, disappear, no_change, uncertain
```

### 2C. Database

Create SQLite tables for objects, zones, events, object_state, queries, metrics, and settings.

Use WAL mode, foreign keys, parameterized queries, and explicit transactions.

Implement:

- initialize database,
- add/list/delete objects,
- add/list/delete zones,
- insert event and update state atomically,
- list events,
- fetch event evidence,
- rebuild current state from accepted events,
- correct event,
- delete all memory while preserving schema,
- get current object location.

### 2D. Default demo data

Add a button or endpoint to load three default zones:

- left_tray,
- center_mat,
- right_tray.

Do not require the zone editor before the first manual demo.

### 2E. Composite builder

Create one composite image containing:

- BEFORE on the left,
- AFTER on the right,
- large headings,
- zone overlays and labels,
- timestamps,
- registered-object reference strip below,
- allowed object and zone IDs in a readable footer.

Save the exact composite used for each inference.

Test dimensions, text presence, and output file creation.

### 2F. VLM client

Create an interface such as:

```python
class VLMClient(Protocol):
    async def analyze_event(self, composite_path: Path, context: EventContext) -> VLMEventResult: ...
    async def answer_from_records(self, question: str, records: list[dict]) -> str: ...
```

Implement:

- real OpenAI-compatible client,
- deterministic mock client selected by environment variable,
- image-to-data-URL conversion,
- timeout and useful errors,
- raw-response logging without secrets,
- temperature 0,
- maximum 512 output tokens,
- optional per-request disabled thinking when supported.

### 2G. Event prompt

Create `app/prompts/event_extractor.txt` with this logic:

- compare visible BEFORE and AFTER evidence,
- select only allowed IDs,
- never infer hidden placement,
- return JSON only,
- report at most one event,
- use uncertain when ambiguous.

The exact JSON schema is:

```json
{
  "event_type": "move|appear|disappear|no_change|uncertain",
  "object_id": "allowed ID or null",
  "from_zone_id": "allowed ID, outside_view, or null",
  "to_zone_id": "allowed ID, outside_view, or null",
  "confidence": 0.0,
  "visible_evidence": ["short observation"],
  "uncertainty_reason": "short reason or null"
}
```

### 2H. Validation and one repair attempt

Implement:

1. remove optional code fences,
2. parse JSON,
3. validate schema,
4. validate IDs,
5. require different zones for move,
6. retry once with `event_repair.txt` if invalid,
7. otherwise produce uncertain with no state mutation.

Auto-accept only above the configured confidence threshold.

### 2I. Manual facade and minimal Gradio UI (NO CAMERA REQUIRED)

The first full vertical slice MUST work with **two explicit images supplied in the browser** (upload or webcam snapshots) even if the presenter laptop camera, Gradio streaming, or network frame ingestion are broken. Implement `LocalRecallFacade.analyze_pair(before_rgb: np.ndarray, after_rgb: np.ndarray) -> EventRecord` using a bounded single-inference worker. The method validates both inputs, builds the composite, analyzes with the local VLM, validates JSON, persists accepted/review events and evidence, and returns the result.

Build a minimal `gr.Blocks` UI on port 7860 that can:

- show TWO SEPARATE non-streaming `gr.Image(sources=["webcam", "upload"], type="numpy")` inputs: `BEFORE` and `AFTER`;
- submit both image arrays to `facade.analyze_pair()` via a queued Analyze button;
- upload PNG/JPEG files in either input when no laptop camera is available;
- load three default zones and enroll at least one object;
- display the event details and BEFORE/AFTER evidence;
- ask where the object is using SQLite-backed answers.

Do not make the manual path depend on Watch Mode, `get_latest_frame()`, a server camera, or an active `.stream()` session. Offline synthetic image fixtures are enough for the first acceptance gate.

For parallel UI development, `python -m app.ui.app --mock --port 7861` must work without model, camera, or database setup. The real mode is `python -m app.ui.app --backend --port 7860`.

Do not proceed until the manual backend flow is tested in both mock inference and real-model mode. UI can be polished in parallel after its contract is frozen.

Commit and tag a known-good baseline:

```bash
git tag manual-mvp
```

## Phase 3: BROWSER camera ingestion and fixture mode (headless Spark)

**No camera is connected to the Spark.** The only live camera is in the presenter laptop/browser. Implement a server-side `BrowserPushSource` with `ingest_frame(frame_rgb, source_id)`, plus a `FixtureSource` for prerecorded files. `app/camera.py` must NOT open `/dev/video*` or call `cv2.VideoCapture(0)`; `cv2.VideoCapture(video_filename)` is allowed solely to decode a fixture or user-uploaded video.

Gradio UI supplies live frames through an **independent streaming-only** image input:

```python
browser_camera = gr.Image(
    label="Laptop Camera (live; starts in the browser)",
    sources=["webcam"],
    type="numpy",
    streaming=True,
)
# source_id can be a gr.State browser-session token, NOT the persistent memory DB.
browser_camera.stream(
    fn=callbacks.ingest_browser_frame,  # calls facade.ingest_frame only
    inputs=[browser_camera, browser_source_id],
    outputs=[browser_ingest_status],
    stream_every=0.5,   # 2 fps; verify on pinned Gradio version
    time_limit=60,
    queue=False,
)
```

The `.stream()` callback MUST return quickly: validate/frame-size-limit/downscale/copy/mark arrival/append to bounded RAM ring; **NEVER** call the VLM or SQLite from that callback. Gradio owns browser camera permission; do not invent a server-camera thread. The browser input displays its own preview; `gr.Timer` polls status/events, NOT source camera frames. Treat Gradio streaming as an optional enhancement to the proven manual image-pair flow.

BrowserPushSource requirements:

- Single active producer/source ID with an expiring 4-second lease. Reject or explicitly switch producers; never interleave two different laptop cameras or silently merge sessions.
- Validate `np.uint8` RGB HxWx3 arrays, reject malformed/empty/oversized input, bound width and height, convert to grayscale for OpenCV only after validation.
- Server-side monotonic reception timestamps (never trust a client wall clock), a bounded 60-frame RAM ring, latest-frame getter for downstream workers, arrival FPS/dropped frame counts, and source-health (`connected`, `source_id`, `seconds_since_last_frame`).
- Default transport ~2 frames/second (640x360 or 960x540 recommended); configurable 1-3 fps. Motion confirmation thresholds must use elapsed time rather than assume 15-fps sampling.
- If no frame arrives for >4 seconds, show `Camera disconnected / browser tab closed` and pause Watch Mode cleanly. Leave the manually uploaded BEFORE/AFTER path functional.
- `FixtureSource` must feed the exact same motion pipeline; generate a synthetic fixture clip or still pair for automated tests. Do not require a USB camera on the Spark.
- Streaming is browser-initiated; it needs a real laptop camera, camera permission, and a live browser tab. The server cannot turn on the laptop camera by itself. Display instructions to click the camera Start control before enabling auto Watch Mode.
- Ensure frontend and backend agree on RGB image orientation and zone overlays; laptop front-facing camera mirrors may invert labels, so calibrate visually before the demo.

Browser camera transport is not the inference path. The backend motion worker consumes `BrowserPushSource` ring-buffer frames asynchronously; once settled, it calls the same `analyze_pair` pipeline as manual mode. There is one bounded VLM inference worker.

Read `HEADLESS_CAMERA_RUNBOOK.md` for SSH/localhost permission, network, offline, and fallback requirements.

## Phase 4: automatic event detection

Implement an ROI-aware motion detector with configurable thresholds.

### Processing

- downscale to 320 x 180,
- grayscale,
- Gaussian blur,
- absolute difference,
- threshold,
- morphological cleanup,
- changed-pixel ratio,
- per-zone changed-pixel ratio.

### State machine

Implement explicit enum states:

```text
NO_CAMERA, STABLE, MOVING, SETTLING, CANDIDATE, ANALYZING, COOLDOWN
```

Behavior:

- In STABLE, preserve the last accepted stable anchor. Only refresh that anchor when there is no meaningful zone difference; NEVER silently overwrite the pre-move anchor with a new scene.
- Enter MOVING after consecutive changed samples OR enter CANDIDATE when a *persistent stable-to-stable scene difference* exists. At ~2fps a fast move can happen entirely between transmitted frames, so inter-frame motion alone must not be the sole trigger.
- Enter SETTLING when movement falls.
- Return to MOVING if movement resumes.
- After sufficient stability, select BEFORE and AFTER.
- Reject candidate if zone-change scores are too small.
- Enqueue at most one analysis.
- Enter cooldown to avoid duplicates.

Suggested starting values, all configurable:

```text
stable_threshold=0.008
moving_threshold=0.025
moving_confirmation_frames=2  # ~2 fps browser sampling; tune using timestamps, not 15-fps assumptions
pre_stable_seconds=1.0
post_stable_seconds=1.2
cooldown_seconds=1.5
```

Write unit tests using synthetic RGB browser frames and prerecorded fixtures. NEVER require `/dev/video*` for unit tests; include a stale-browser-disconnect test and a second-producer rejection test.

Expose Watch Mode start/stop through facade methods. A `gr.Timer` refreshes lightweight status, ingestion health, and event records every 0.5 to 1.0 seconds with `queue=False`; never run inference or echo the live browser camera from a timer callback.

## Phase 5: object enrollment and zone editor

### Object enrollment

Implement:

1. capture snapshot,
2. let the user provide a normalized crop rectangle,
3. save a 256 x 256 reference crop,
4. collect display name and aliases,
5. validate unique lowercase slug ID,
6. show reference card.

Limit the UI to five active objects in demo mode.

### Zone configuration

For the MVP use three default rectangular zones and a simple Setup form for names and normalized rectangle coordinates (`x1, y1, x2, y2`). Show zone overlays in the Gradio preview. Gradio does not require a draggable JavaScript canvas. A direct-manipulation zone editor is a stretch goal only after the manual and automatic demos work.

## Phase 6: query service

Implement deterministic queries first:

- Where is OBJECT?
- When was OBJECT last moved?
- What moved most recently?
- List current locations.
- Show event NUMBER.

Resolve object names through IDs, display names, aliases, and conservative fuzzy matching.

Answer from SQLite only. Include event IDs and evidence.

Then add a local-model fallback for broader questions. Retrieve a small set of relevant records and prompt the model to:

- answer only from records,
- cite event IDs,
- say unknown when evidence is missing,
- never infer an unobserved location.

Do not use the model as the memory database.

## Phase 7: polished Gradio interface

Build `gr.Blocks` in `app/ui/app.py` using these five tabs:

1. **Watch**: browser webcam `gr.Image(sources=["webcam"], streaming=True)` with live self-preview and ingest-health badge; separate manual BEFORE/AFTER `gr.Image(sources=["webcam", "upload"])` inputs, queued Analyze button, Start/Stop Watch, motion status, latest evidence. Add an explicit Upload Pair fallback.
2. **Memory**: current object locations in a `gr.Dataframe`, recent event history, BEFORE/AFTER evidence gallery, approve/reject review events.
3. **Ask**: question textbox, suggested question controls, database-backed answer and clickable evidence reference.
4. **Setup**: browser-camera/fixture/paired-image source indicator, object enrollment via `gr.Image`, names and aliases, default zone loader, basic zone coordinate editor.
5. **System & Privacy**: real health and offline status, Qwen model name, inference latency, retained evidence count, export, and confirmed Delete All Memory.

Use `gr.Timer` every 0.5-1.0 seconds only for cheap `get_status()`, frame-age/ingest-health metrics, and bounded table reads, with `queue=False`. The browser-camera preview lives inside its own streaming input; polling must NOT send its own `get_latest_frame()` back into that component. Polling never calls Qwen. Use queued button handlers for long operations and make their busy/error states visible. `gr.State` may hold selected UI IDs, never the authoritative event history or camera/model service. UI callbacks must be in `app/ui/callbacks.py`, formatting in `app/ui/transforms.py`, and all backend access through `app/facade.py`.

No separate FastAPI server, custom HTML/JS frontend, extra WebSockets, remote assets, or Gradio public `share=True` links. Gradio runs on the headless Spark; the laptop browser OWNS the camera and streams frames to it. Bind `127.0.0.1`, access over SSH `-L` tunnel via `http://127.0.0.1:7860` on the laptop so browser webcam permission works. Default camera sampling and size must be configurable. Include graceful camera-denied and webcam-absent fallback to manual image upload.

The UI must look approachable and provide clear evidence, not raw diagnostic JSON. A detailed technical view can be secondary. Test the UI against the mock facade before connecting to the real one.

## Phase 8: privacy enforcement

Implement technical safeguards:

- no continuous video writer in normal mode,
- bounded in-memory ring buffer,
- account for Gradio temporary-upload/image cache files: set a dedicated `GRADIO_TEMP_DIR` if compatible, bound retention, test cleanup, disclose unavoidable temporary files, and exclude them from evidence; do not claim zero temporary frame bytes if this has not been verified,
- persist only event evidence,
- central function that validates local URLs,
- offline environment variables,
- Delete All Memory removes event images and database content transactionally,
- clear confirmation dialog,
- tests proving deletion,
- log an error if an outbound non-local model URL is configured in offline mode.

Implement `scripts/check_offline.sh` that verifies:

- VLM URL is loopback,
- app URL is local,
- model and app still answer when external connectivity is unavailable or blocked BUT the presenter laptop still has LOCAL connectivity to the Spark,
- no cloud credentials are required.

Do not change host firewall rules automatically. Document optional manual network-disconnect steps instead.

## Phase 9: metrics and evaluation

Instrument:

- browser-frame ingest FPS, last-frame age, source/disconnect count,
- motion events seen,
- VLM calls,
- VLM failures,
- model latency,
- end-to-end event latency,
- accepted/review/uncertain counts,
- query latency.

Create `scripts/run_eval.py` and a fixture format for ground truth.

Evaluation set must support at least 20 trials containing:

- clear moves,
- hand motion with no object move,
- object appearance,
- object disappearance,
- one ambiguous event.

Calculate:

- event precision,
- event recall,
- object-ID accuracy,
- destination-zone accuracy,
- median and p95 model latency,
- end-to-end median latency,
- false positives,
- continuous-video bytes stored.

If a metric cannot be measured, print `not measured`; never invent it.

## Phase 10: in-process application contract

Do not implement a separate REST API for the hackathon UI. The OpenAI-compatible local model endpoint on `localhost:8000` is the only HTTP boundary required by the application. Build the shared Python contract defined below and test it end-to-end with mock and real backend implementations.

## Python facade: one shared contract

Gradio and backend communicate through direct Python calls, not a new HTTP API. Implement `app/facade.py` as the adapter to backend services and `app/contracts.py` for dataclasses/Pydantic schemas. Publish these methods before UI work begins:

```python
class LocalRecallFacade(Protocol):
    def get_status(self) -> SystemStatus: ...
    def get_latest_frame(self) -> np.ndarray | None: ...  # latest browser-ingested/fixture frame
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

Implement both real and mock facades. The mock returns deterministic fixture records and must NOT open the camera, start vLLM, or connect to the model. The real facade owns a single backend-service instance. The backend BrowserPushSource owns in-memory copies of frames received from the browser; `cv2.VideoCapture` may only open an uploaded/fixture VIDEO FILE, never a local webcam device. Event history, object state, and privacy settings persist in SQLite, not `gr.State`. Synchronous facade calls may delegate to a worker; do not block Gradio's polling callbacks on model inference.

Use these application entrypoints:

```bash
python -m app.ui.app --mock --port 7861
python -m app.ui.app --backend --port 7860
```

The normal launch script binds backend-mode Gradio to `127.0.0.1:7860`, reachable from the presenter laptop using `ssh -N -L 7860:127.0.0.1:7860 <user>@<SPARK_LAN_IP>` and browsing `http://127.0.0.1:7860`. Browser `localhost` is a secure context for webcam access; plain `http://SPARK_IP:7860` may NOT access the webcam. Gradio public share is disabled. The model endpoint binds only `127.0.0.1:8000`. Do NOT add a second camera capture service.

## Phase 11: tests and quality gates

Create and run tests for:

- schemas,
- database initialization,
- transactional event insertion,
- state rebuild,
- correction,
- alias resolution,
- deterministic query answers,
- composite generation,
- motion state transitions,
- fixture video,
- mock model pipeline,
- facade health, manual image-pair flow, browser-frame ingestion/session/timeout, mock Gradio callback outputs,
- privacy deletion,
- offline URL enforcement.

Provide Makefile commands:

```text
make preflight
make setup
make model-start
make model-smoke
make run
make test
make eval
make demo-bundle
make stop
```

`make test` must not require the real model or camera.

`make model-smoke` may require the real model.

## Phase 12: documentation and demo assets

### README.md

Include:

- problem,
- solution,
- architecture,
- requirements,
- quick start,
- offline operation,
- privacy design,
- limitations,
- measured results,
- troubleshooting.

### RUNBOOK.md

Include exact cold-start steps:

1. start model on headless Spark;
2. wait for model health;
3. start Gradio bound to Spark localhost;
4. open SSH `-L` port forward from presenter laptop;
5. open `http://127.0.0.1:7860` in laptop browser and grant webcam access there;
6. use manual BEFORE/AFTER snapshots/uploads FIRST, then optionally start streamed Watch Mode;
7. load demo profile and run smoke event;
8. stop services.

Reference `HEADLESS_CAMERA_RUNBOOK.md` for exact connection and troubleshooting commands.

### DEMO_SCRIPT.md

Create a three-minute script:

- problem,
- local-only badge and LAN/SSH link still active,
- live move observed in the laptop browser or uploaded BEFORE/AFTER pair,
- question,
- evidence,
- architecture,
- actual metrics,
- impact.

### ARCHITECTURE.md

Include Mermaid diagrams for:

- data flow,
- event state machine,
- database flow.

### Backup

Create `scripts/export_demo_bundle.sh` that archives:

- source excluding model caches,
- README and runbook,
- known-good database or demo profile,
- screenshots,
- evaluation output,
- backup video path if present,
- Git commit ID.

Do not include huge model weights.

## Required event prompt

Use this as the initial `event_extractor.txt`, filling template variables at runtime:

```text
You are LocalRecallEventExtractor, a conservative visual change analyzer.

The supplied composite image contains a BEFORE scene, an AFTER scene, labeled spatial zones, and registered-object reference images.

Allowed object IDs:
{{OBJECT_IDS}}

Allowed zone IDs:
{{ZONE_IDS}}

Return exactly one JSON object:
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
1. Use only visible evidence in BEFORE and AFTER.
2. Do not invent an object, zone, or hidden destination.
3. Select IDs only from the supplied allowed values.
4. Use move only when the same registered object clearly changes location.
5. Use appear when absent before and visible after.
6. Use disappear when visible before and absent after.
7. Use no_change if motion occurred but no registered object changed.
8. Use uncertain when evidence is ambiguous.
9. If multiple objects moved, report the clearest one and lower confidence.
10. Output JSON only, without Markdown.
```

## Required database behavior

SQLite must use WAL and foreign keys. Implement tables for:

- objects,
- zones,
- events,
- object_state,
- queries,
- metrics,
- settings.

Accepted `move` and `appear` events update state. `disappear` moves state to outside_view or unknown. `no_change` and `uncertain` do not update state. Corrections trigger a deterministic state rebuild.

## Required confidence behavior

Defaults:

```text
confidence >= 0.70: auto-accept
0.45 <= confidence < 0.70: review queue
confidence < 0.45: uncertain and no state change
```

Make thresholds configurable.

## Required manual fallback

Manual mode is a first-class feature, not hidden debugging code. It must remain usable in the final UI even if automatic Watch Mode works.

## Feasibility stop rules

- If vision inference is not working within 90 minutes, switch runtime or model fallback.
- If a manual end-to-end event is not working within roughly three hours, stop all noncritical work and repair it.
- If automatic browser-camera ingestion/detection is unreliable near demo time, present Manual Remember using uploaded or webcam-snapshot image pairs as the reliable interaction and describe Watch Mode as beta.
- Do not perform architectural rewrites on the final morning.

## Parallel team preparation

After `app/contracts.py` and the mock facade are scaffolded and committed, create worktrees immediately, without waiting for the full manual MVP:

```bash
git worktree add ../localrecall-ui -b feature/ui
git worktree add ../localrecall-eval -b feature/eval
```

Create these task files:

- `TASK_UI.md`: only `app/ui/**`, `tests/test_ui_contract.py`, and UI handoff docs may be changed. The UI agent must not edit `app/facade.py` or `app/contracts.py`.
- `TASK_EVAL.md`: only `scripts/run_eval.py`, `tests/fixtures/**`, demo docs, and presentation content may be changed.

Provide explicit acceptance criteria in each file. Keep backend contracts stable so less-technical team members can direct their Codex agent through browser-visible results rather than terminal knowledge.

## Completion report

At the end of each major phase, report in `STATUS.md`:

- Git commit,
- implemented functionality,
- commands run,
- tests run and exact outcome,
- model and app health,
- measured latency if available,
- known limitations,
- next task.

When the project is complete, print a concise operator summary containing:

1. exact command to start the model,
2. exact command to start the app,
3. local URL,
4. demo steps,
5. how to stop everything,
6. known-good Git tag,
7. unresolved risks.

Begin now with Phase 0. Do not stop after writing documentation; continue through implementation and verification. **Do the manual uploaded-image-pair MVP before investigating browser streaming.**
