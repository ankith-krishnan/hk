# Backend: Connect LocalRecall to the local model and memory

## Your mission

You own the part that makes LocalRecall actually work: the Python facade, model connection, image analysis, SQLite memory, local vLLM setup, and backend checks. Frontend A and Frontend B build Gradio pages. They call your backend using the `LocalRecallFacade` contract in `app/contracts.py`.

The main product path is:

1. Receive BEFORE and AFTER pictures from the laptop browser.
2. Validate the pictures and build a labeled comparison image.
3. Send that image to Qwen running locally on the GB10.
4. Parse and validate the model’s structured event response.
5. Store the event and its evidence in SQLite.
6. Answer questions using the stored, validated events.

Keep this order. The manual image-pair path is the first acceptance target. Automatic motion detection comes later and stays off until the real model passes the image gate.

## Current starting point

The repository already includes a backend scaffold:

- `app/contracts.py`: the shared UI/backend function agreement.
- `app/facade.py`: coordinates frame input, analysis, storage, queries, and privacy.
- `app/config.py`: settings and loopback-only VLM URL check for offline mode.
- `app/vlm_client.py`: real OpenAI-compatible local client and deterministic mock client.
- `app/event_analyzer.py`: parses model JSON, validates IDs, and allows one repair attempt.
- `app/memory_store.py`: SQLite tables, event history, and current-state projection.
- `app/composite.py`: creates the labeled BEFORE/AFTER image sent to the model.
- `app/camera.py`: browser frame ring and video-file fixture decoder. It must never use a server camera device.
- `scripts/start_vllm.sh`, `scripts/wait_for_vllm.sh`, and smoke scripts: model runtime checks.

Some of these files already contain uncommitted changes. Do not reset, clean, or overwrite the shared worktree. Ask the integrator to save a checkpoint commit before creating a branch.

## Important environment status

The machine inspected so far is Ubuntu ARM64 with an NVIDIA GB10. The partial Hugging Face Qwen cache was removed at the user's request. Direct `docker` still cannot access `/var/run/docker.sock`, but passwordless `sudo -n docker info` works and the user has authorized its use. The `vllm/vllm-openai:qwen38` runtime image is being pulled. Do not claim that Qwen weights are inside that image or that Qwen inference has run. The next step is to store weights in a persistent Docker-managed volume.

The organizer’s ASUS GX10 identity has not been confirmed. Record the actual machine before describing it as the judging target.

## Your files

Primary ownership:

- `app/contracts.py`
- `app/config.py`
- `app/facade.py`
- `app/vlm_client.py`
- `app/event_analyzer.py`
- `app/memory_store.py`
- `app/camera.py`
- `app/composite.py`
- `app/query_service.py`
- `app/schemas.py`
- `app/prompts/`
- `scripts/start_vllm.sh`, `scripts/wait_for_vllm.sh`, `scripts/stop_vllm.sh`, `scripts/smoke_*.py`
- backend tests under `tests/`

Coordinate before changing `app/contracts.py`. It is the border between your work and both frontend contributors’ work.

## Phase 1: Prepare the Python project

From your backend worktree:

```bash
make setup
make test
make lint
```

The tests use mock inference and do not need Docker, a camera, or Qwen. Fix failing tests before debugging the real model; this separates app bugs from model-serving bugs.

Read these files in order:

1. `app/schemas.py` — the shapes of events, objects, zones, queries, and status.
2. `app/contracts.py` — the functions Gradio is allowed to call.
3. `app/facade.py` — how those functions are implemented.
4. `app/event_analyzer.py` and `app/vlm_client.py` — model request and response validation.
5. `app/memory_store.py` and `app/query_service.py` — persistence and evidence-backed answers.

## Phase 2: Finish the manual backend path

Use mock mode first. The backend should let a caller pass two RGB images into `analyze_pair()` without starting a camera stream. Check that it:

- rejects a missing, malformed, oversized, or non-RGB image;
- requires an enrolled object and named zones;
- keeps only one model request active at a time;
- builds a composite that visibly labels BEFORE, AFTER, zones, object IDs, and the paired timestamp;
- calls the `VLMClient` interface rather than hard-coding HTTP calls in the facade;
- validates every object and zone ID against the current registry;
- performs at most one repair request for invalid JSON;
- stores visible evidence and both input images for accepted/reviewable records;
- writes the event and accepted object-state change in one SQLite transaction;
- answers location questions from SQLite and cites the event that supports the answer.

Use `make test` to prove the mock path. The loopback mock HTTP server tests request formatting only. Never describe its output as Qwen inference.

## Phase 3: Get Docker and the checkpoint ready

First confirm Docker works for this account:

```bash
sudo -n docker info
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

This machine currently requires `sudo -n docker`; project scripts now support that fallback. If it asks for a password or stops working, ask the machine owner. Do not change groups or socket permissions from the app setup script.

The model weights are kept in a persistent Docker volume named `localrecall-qwen38-cache`, not copied into the vLLM runtime image or the host HF cache. On first start, the launcher downloads them into that volume using the image's Python `huggingface_hub` package. Later starts reuse the volume and verify the index and every shard.

Inspect and start the chosen Spark image and model:

```bash
./scripts/start_vllm.sh
./scripts/wait_for_vllm.sh
```

The launcher checks the image entrypoint and its `vllm serve --help` before it starts. If a flag is not supported, inspect the actual image help and update the launcher deliberately. Do not guess a command copied from a different vLLM release.

## Phase 4: Pass real model gates

Run:

```bash
make model-smoke
```

This runs one text request and image/event requests against the local endpoint. Image inference is a separate gate: a passing text request is not enough. Save the request images and raw model response in the smoke fixture folder. Record the model name, endpoint, return code, and latency exactly as observed.

If text works but image input does not, do not enable automatic Watch Mode. Inspect the vLLM logs and image recipe. The project plan permits trying a Spark-compatible SGLang runtime behind the same `VLMClient` boundary. Keep the Gradio facade and data model stable while testing that alternative.

## Phase 5: Run the real manual UI path

After real image smoke succeeds:

```bash
.venv/bin/python -m app.ui.app --backend --host 127.0.0.1 --port 7860
```

Open it from the presenter laptop through an SSH localhost forward:

```bash
ssh -N -L 7860:127.0.0.1:7860 <spark-user>@<spark-lan-ip>
```

On the laptop, upload or snapshot BEFORE and AFTER images, enroll an object, load zones, analyze the pair, inspect the event pictures, then ask where the object is. Confirm that the answer names an event ID and points to saved evidence. Confirm that low-confidence or invalid model output does not update current location.

The laptop browser owns the webcam. Never require `/dev/video*` on the GB10 and never open `cv2.VideoCapture(0)`. The only allowed `VideoCapture` is for decoding a fixture or uploaded video file.

## Phase 6: Only then consider automatic Watch Mode

The current browser stream only reports ingress health. Do not change that status to event detection until you implement and verify the full pipeline. The future pipeline needs a bounded stable-frame ring, stale-source handling, inexpensive OpenCV motion scores, stable BEFORE/AFTER selection, zone-aware candidate filtering, cooldown, and an event-triggered VLM request. It must not send every video frame to Qwen or write continuous video.

Build this behind a clear setting/feature gate. Test it with generated fixture video and synthetic browser frames before trying the laptop camera. Keep manual analysis available if the stream stops or the motion result is unclear.

## Data and privacy rules

- SQLite is the factual source of truth; model prose is not.
- Use validated Pydantic records and only allowed object/zone IDs.
- Use explicit SQLite transactions and keep event history separate from rebuildable current state.
- Send model requests only to the configured loopback endpoint while `OFFLINE_MODE=1`.
- Do not store continuous video. Store only explicit event evidence and enrolled reference images.
- Gradio can create temporary image files. Keep those in the configured dedicated directory, enforce the retention/size limit, report the measured directory size, and test deletion.
- Never print tokens, passwords, request authorization headers, or private image contents into logs.

## What to record in `STATUS.md`

After every gate, write down:

- the exact command;
- whether it passed or failed;
- actual model and machine names;
- test counts and measured latency;
- whether the result used mock or real inference;
- what remains untested.

Write “not measured” when no measurement exists. Do not fill gaps with estimates.

## Definition of done for your role

- Existing mock tests, lint, and local HTTP integration pass.
- Docker GPU access is verified for the correct machine.
- Checkpoint snapshot is complete and vLLM starts without discarding an existing container.
- Real text and image smoke tests pass; raw results are retained.
- Manual pair → validated event → SQLite → Ask/evidence works through Gradio.
- Watch Mode stays disabled until a separately tested event-triggered pipeline exists.
- Backend contract changes are written down and shared with both frontend contributors.
