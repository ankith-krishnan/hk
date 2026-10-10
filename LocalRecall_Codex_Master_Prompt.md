# Master Prompt for Codex: Build LocalRecall

Copy everything below into the primary Codex agent while it is opened at the root of a new repository on the Ubuntu 24.04 DGX Spark / ASUS GX10-class machine.

---

You are the principal implementation agent for a time-constrained local-AI hackathon project named **LocalRecall**.

Your job is to autonomously build, test, document, and harden a complete working application on the current machine. Work incrementally and keep a runnable vertical slice at all times. Do not merely write a plan. Inspect the machine, create the repository, implement the code, run tests, start services, exercise endpoints, and record concrete results.

## Product objective

Build a private visual-memory appliance for a bounded tabletop workspace. It must:

1. Capture a fixed USB webcam or fixture video.
2. Let the user define three to four named spatial zones.
3. Let the user enroll three to five named objects with reference images and aliases.
4. Detect the start and end of meaningful motion using cheap OpenCV processing.
5. Select one clean BEFORE frame and one clean AFTER frame.
6. Build one labeled composite image containing BEFORE, AFTER, zone overlays, and registered-object references.
7. Send that composite to the local model `nvidia/Qwen3.8-27B-NVFP4`.
8. Receive and validate strict structured JSON describing at most one object event.
9. Store the accepted event in SQLite and update deterministic current object state.
10. Answer questions such as `Where are my keys?` with event evidence.
11. Run without a cloud API and without saving continuous raw video.
12. Provide a polished local web UI and a manual BEFORE/AFTER fallback.

The final live demonstration must work with external internet disabled after dependencies and model artifacts are present.

## Current machine and model assumptions

- Ubuntu 24.04 LTS.
- NVIDIA GB10 Blackwell-class integrated GPU/CPU.
- 128 GB unified memory.
- 4 TB local storage.
- Docker and NVIDIA Container Toolkit should be available.
- The Hugging Face cache already contains:
  - `nvidia/Qwen3.8-27B-NVFP4`
  - `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16`
  - `nvidia/Alpamayo-1.5-10B`
  - `nvidia/Cosmos3-Nano`
- Use only `nvidia/Qwen3.8-27B-NVFP4` in the MVP.
- The preferred Spark-specific image is `vllm/vllm-openai:qwen38`.
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

- Backend: Python 3.11 or 3.12, FastAPI, Uvicorn.
- Frontend: vanilla HTML, CSS, and JavaScript served by FastAPI. No required Node build.
- Vision gate: OpenCV and NumPy.
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
lsusb || true
v4l2-ctl --list-devices || true
ls -l /dev/video* 2>/dev/null || true
find "$HOME/.cache/huggingface/hub" -maxdepth 3 -type d -name '*Qwen3.8-27B-NVFP4*' 2>/dev/null || true
docker image ls
```

Write the result and interpretation into `STATUS.md` under `Environment Preflight`.

Do not dump secrets into tracked files.

Initialize Git if necessary and create the first commit containing only documentation and scaffold files.

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
APP_HOST=0.0.0.0
APP_PORT=8080
DATA_DIR=./data
DATABASE_PATH=./data/localrecall.db
VLM_BASE_URL=http://127.0.0.1:8000/v1
VLM_MODEL=nvidia/Qwen3.8-27B-NVFP4
VLM_TIMEOUT_SECONDS=180
OFFLINE_MODE=1
CAMERA_INDEX=0
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

### 2I. Manual endpoints and UI

Implement:

- `POST /api/manual/before`
- `POST /api/manual/after`

The first captures or uploads BEFORE. The second captures AFTER, builds composite, invokes the model, validates, stores, and returns the event.

Build a basic browser UI that can:

- show a camera or fixture preview,
- load default zones,
- enroll at least one object,
- capture BEFORE,
- capture AFTER and analyze,
- show returned event,
- ask where the object is,
- show evidence.

Do not proceed until this entire vertical slice works with both mock inference and the real local model.

Commit and tag a known-good baseline:

```bash
git tag manual-mvp
```

## Phase 3: camera service and fixture mode

Implement one camera-owning background thread.

Requirements:

- `cv2.VideoCapture` used in one place only,
- requested 1280 x 720 at 15 FPS,
- thread-safe latest-frame access,
- 60-frame bounded ring buffer,
- downscaled grayscale frame for motion,
- MJPEG preview endpoint,
- camera-health metrics,
- fixture-video implementation with the same interface,
- graceful release on shutdown.

If no camera exists, automatically enter fixture mode and display that fact clearly.

Implement a script that creates a deterministic fixture video containing a colored object moved between zones. Use it in tests.

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

- In STABLE, continuously update a clean anchor frame only after a stable duration.
- Enter MOVING after several frames above the movement threshold.
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
moving_confirmation_frames=3
pre_stable_seconds=1.0
post_stable_seconds=1.2
cooldown_seconds=1.5
```

Write unit tests using synthetic frames. Never require a real camera for unit tests.

Add Watch Mode start/stop APIs and stream state changes over WebSocket.

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

### Zone editor

Implement a canvas overlay that:

- freezes a current snapshot,
- lets the user drag rectangles,
- converts coordinates to normalized values,
- names the zone,
- renders saved zones over live video,
- supports default demo zones.

Use a simple rectangle UI. Do not build arbitrary polygon editing unless everything else is complete.

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

## Phase 7: polished interface

Build one responsive single-page UI with these tabs:

1. Live
2. Objects
3. Zones
4. Memory
5. Ask
6. Privacy and System

### Live tab

Show:

- live feed,
- zone overlays,
- Watch Mode,
- state pill,
- motion score,
- last event,
- Manual Remember controls.

### Objects tab

Show enrollment wizard, references, names, and aliases.

### Zones tab

Show zone editor and default-layout button.

### Memory tab

Show event cards with BEFORE, AFTER, confidence, status, accept, and correct controls.

### Ask tab

Show question input, answer, evidence, and example questions.

### Privacy and System tab

Show:

- local model name,
- model endpoint health,
- offline status,
- event count,
- stored-image count,
- statement that continuous video is not stored,
- Delete All Memory,
- measured model latency,
- VLM call count.

The interface should look like a product, not Swagger UI. Use readable typography, a restrained palette, clear status indicators, and large evidence cards.

## Phase 8: privacy enforcement

Implement technical safeguards:

- no continuous video writer in normal mode,
- bounded in-memory ring buffer,
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
- model and app still answer when external connectivity is unavailable or blocked,
- no cloud credentials are required.

Do not change host firewall rules automatically. Document optional manual network-disconnect steps instead.

## Phase 9: metrics and evaluation

Instrument:

- camera FPS,
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

## Phase 10: API surface

Implement and document at least:

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

Add OpenAPI descriptions, but the primary UI must not depend on Swagger.

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
- API health and manual flow,
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

1. connect camera,
2. start model,
3. wait for health,
4. start app,
5. open UI,
6. load demo profile,
7. run smoke event,
8. stop services.

### DEMO_SCRIPT.md

Create a three-minute script:

- problem,
- offline badge,
- live move,
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
- If automatic detection is unreliable near demo time, present Manual Remember as the reliable interaction and describe Watch Mode as beta.
- Do not perform architectural rewrites on the final morning.

## Parallel team preparation

After the manual MVP is committed, create worktrees:

```bash
git worktree add ../localrecall-ui -b feature/ui
git worktree add ../localrecall-eval -b feature/eval
```

Create these task files:

- `TASK_UI.md`: only `app/static/**` and narrowly related tests may be changed.
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

Begin now with Phase 0. Do not stop after writing documentation; continue through implementation and verification.
