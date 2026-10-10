# LocalRecall Team Task Prompts

These prompts assume the primary Codex agent has already scaffolded and committed `app/contracts.py` and the mock facade, so the real manual MVP can be built in parallel. Use Git worktrees so the three agents do not edit the same files.

---

# Setup by the technical member

Run once from the main repository after the shared facade contract and mock scaffold commit:

```bash
git worktree add ../localrecall-ui -b feature/ui
git worktree add ../localrecall-eval -b feature/eval
```

Open three separate Codex threads or windows:

- Core agent at the main repository.
- UI agent at `../localrecall-ui`.
- Evaluation/demo agent at `../localrecall-eval`.

The two less-technical members must NOT be required to use SSH, `git`, or terminal commands. The core member opens the worktrees, starts the Gradio UI/mock service, and establishes the SSH port forward on the presenter laptop. Friends interact through the local browser and their already-open Codex sessions. The camera lives in the PRESENTER LAPTOP, not in the headless Spark.

---

# Prompt A: Gradio Product Experience Member

You own ONLY the Gradio UI for LocalRecall. The core member owns Qwen serving, **browser-frame ingestion logic (not local USB camera access)**, memory, backend behavior, `app/facade.py`, and `app/contracts.py`. Build a clean, reliable, visually compelling UX against a **mock facade first**, and do not attempt to take over backend work.

## Path ownership

You may edit only:

```text
app/ui/**
tests/test_ui_contract.py
TASK_UI.md
UI_HANDOFF.md
```

Read `LocalRecall_Implementation_Blueprint.md` sections 19-20, `app/contracts.py`, `AGENTS.md`, and `README.md`. If `app/contracts.py` is missing, write the required contract request into `UI_HANDOFF.md` and proceed using a locally typed mock for the documented methods; do not modify backend code. Write a brief plan to `TASK_UI.md`.

## Mandatory stack and launch modes

Use **Python Gradio Blocks** only. Do NOT build React/Vite/Vue, custom HTML/CSS/JS client files, a FastAPI HTTP application layer, or WebSockets. Put the UI in `app/ui/app.py`, the callback wrappers in `app/ui/callbacks.py`, rendering helpers in `app/ui/transforms.py`, and fixture-only mock implementation in `app/ui/mock_facade.py`.

The following must launch cleanly without any model download or camera:

```bash
python -m app.ui.app --mock --port 7861
```

Integrate with the real backend facade when the core developer provides it:

```bash
python -m app.ui.app --backend --port 7860
```

Do not instantiate models or camera captures from UI modules. All calls go through the facade protocol. Do not make fake data look like real recorded events in backend mode.

## Product screens

Implement five tabs:

1. **Watch**: optional browser-owned `gr.Image(sources=["webcam"], type="numpy", streaming=True)` for live preview/automatic Watch; TWO SEPARATE non-streaming `gr.Image(sources=["webcam", "upload"], type="numpy")` inputs labeled BEFORE and AFTER with Analyze button invoking `facade.analyze_pair`. Show stale/unavailable source and retain upload-only mode. Do NOT poll server webcam.
2. **Memory**: current object table, event timeline, review queue, approve/reject controls, before/after/comparison evidence gallery.
3. **Ask**: textbox, examples, database-backed answer, event ID, image, confidence. Never invent answers.
4. **Setup**: object enrollment (`gr.Image` crop/upload or backend snapshot), default three zones, simple named normalized rectangle inputs. No JavaScript canvas is required.
5. **System & Privacy**: true current health/offline/model status, event/evidence counters, Export Session, Delete All Memory with explicit confirmation.

Prefer a simple, readable interface over elaborate styling. Put technical details in a small optional section. Keep all assets local and Gradio sharing disabled.

## Timers, responsiveness, and error handling

Use `gr.Timer` to call lightweight facade getter methods every 0.5-1.0 seconds with `queue=False`. **The browser owns the webcam.** Register `.stream()` on the webcam-only input with `stream_every=0.5`, `time_limit=60`, `queue=False`, and an INGEST-ONLY callback calling `facade.ingest_frame`. A `gr.State` session ID may identify the producer; do not store object memory there. Never run inference from a streaming or timer handler. Long-running manual analysis must be a queued action; display a busy indicator and restore button state on failure. `gr.State` is only for ephemeral UI selections, not object history, model process, or camera objects.

If an operation errors, display the error to the user; never silently swallow it. Do not create fake online/offline status. No external CDN, fonts, analytics, model APIs, or Gradio share tunnels. The app is visited from the laptop via `http://127.0.0.1:7860` using an SSH local port forward configured by the core member; do not ask friends to use raw `http://SPARK_IP:7860` for webcam access (browser secure-context restrictions).

## Acceptance checklist

Verify in mock mode with browser and tests:

1. Launch UI at `localhost:7861` without model/camera.
2. Show all five tabs and realistic fixture data clearly marked MOCK.
3. Upload or capture BEFORE and AFTER in two distinct browser inputs, click Analyze, and show an evidence record; it must NOT require an active stream.
4. Ask where the keys are; show answer and evidence.
5. Show pending review and approve/reject path.
6. Show empty and backend error states.
7. Show confirmation for destructive data deletion.
8. Start a laptop-browser webcam stream and verify ingress status increments in mock mode without model or Spark camera.
9. Stop/close browser camera and verify stale/disconnected indicator.
10. Run `pytest tests/test_ui_contract.py` with actual results.

## Handoff

Commit only owned files and write `UI_HANDOFF.md` with changed paths, test results, screenshots if available, and any missing backend-facade methods. Do not merge your worktree yourself.

# Prompt B: Evaluation, Demo, and Submission Member

You are the evaluation and demo agent for LocalRecall. A separate core agent owns the backend and model integration. Your job is to create reproducible tests, honest metrics, demo materials, and a submission-ready explanation.

## Path ownership

You may modify only:

```text
scripts/run_eval.py
scripts/make_fixture_video.py
scripts/export_demo_bundle.sh
tests/fixtures/**
data/fixtures/**
DEMO_SCRIPT.md
EVALUATION.md
DEVPOST_DRAFT.md
PITCH_QA.md
TASK_EVAL.md
EVAL_HANDOFF.md
README.md sections explicitly marked RESULTS or DEMO
```

Do not modify model-serving scripts, database implementation, motion implementation, facade methods, or UI files. If a required facade capability is missing, document it in `EVAL_HANDOFF.md`.

## Read first

Read:

- `AGENTS.md`
- `README.md`
- `ARCHITECTURE.md`
- `RUNBOOK.md`
- the Python facade contract in `app/contracts.py`
- existing event and evaluation schemas

Write a short plan into `TASK_EVAL.md` before editing.

## Evaluation objective

Create a repeatable trial set that measures what the product actually claims. Never invent results.

The trial specification must support:

- trial ID,
- object ID,
- expected event type,
- expected source zone,
- expected destination zone,
- video or image fixture path,
- expected ambiguity flag,
- notes.

Create at least 20 planned trials across:

- clear moves,
- hand passes with no object movement,
- object appearance,
- object disappearance,
- one ambiguous or occluded event,
- multiple different objects,
- all demo zones.

## Evaluation script

`run_eval.py` should:

1. Load a JSONL or CSV manifest.
2. Evaluate each fixture through the backend/facade or direct event analyzer (no REST API required).
3. Record raw predictions.
4. Compare predictions with ground truth.
5. Calculate, when data exists:
   - event precision,
   - event recall,
   - event-type accuracy,
   - object-ID accuracy,
   - source-zone accuracy,
   - destination-zone accuracy,
   - median model latency,
   - p95 model latency,
   - median end-to-end latency,
   - false-positive count.
6. Write machine-readable JSON and human-readable Markdown output.
7. Print `not measured` instead of inventing unavailable values.
8. Exit nonzero only for execution failure, not because accuracy is imperfect.

Support a mock mode for development and a real mode for final measurement.

## Fixture support

Improve `make_fixture_video.py` so it can generate deterministic synthetic fixtures with:

- labeled zones,
- colored object shapes,
- stable beginning,
- visible movement,
- stable ending,
- configurable no-change case.

Also create a folder structure for real recorded trials. Do not commit large videos unless the team explicitly decides to.

## Demo script

Create a three-minute script with exact speaking roles for three people.

Suggested division:

- Member 2: problem and user value.
- Member 3: live product interaction.
- Technical member: architecture, NVFP4, and measured result.

The script must include:

1. Problem in one sentence.
2. Why cloud camera memory is undesirable.
3. LocalRecall solution.
4. Offline badge.
5. Move one object.
6. Ask where it is.
7. Open evidence.
8. Explain event-triggered inference.
9. Explain SQLite as factual memory.
10. State real measured results.
11. End with privacy and impact.

Create a fallback version using uploaded BEFORE and AFTER screenshots (and a prerecorded short video if available), so the demo survives browser camera denial, lack of camera, dropped SSH stream, or UI streaming failure. Do not rely on a USB camera connected to Spark.

## Devpost draft

Create `DEVPOST_DRAFT.md` with:

- project name and tagline,
- inspiration,
- what it does,
- how it was built,
- why local AI is essential,
- technical architecture,
- challenges,
- accomplishments,
- lessons learned,
- limitations,
- future work,
- setup instructions,
- team contributions.

Do not claim production readiness or universal object recognition.

## Judge Q&A

Create `PITCH_QA.md` with concise answers to likely questions:

- Why not use a cloud API?
- Why Qwen3.8 NVFP4?
- Why not run the VLM on every frame?
- What happens when the model is wrong?
- Is video stored?
- How do you prove inference works without external WAN while the laptop-to-Spark LAN remains connected?
- Why must the browser use localhost/HTTPS to access its webcam?
- What happens when the laptop tab closes and the stream stops?
- Why is SQLite the source of truth?
- What are the current limitations?
- What did each member build?
- How would this scale beyond one desk?

## Backup bundle

`export_demo_bundle.sh` should collect source, docs, screenshots, evaluation outputs, current Git commit ID, and a path reference to the backup video. It must exclude model caches, virtual environments, and large temporary files.

## Handoff

When done:

1. Run evaluation in mock mode.
2. Run any available real trials without fabricating missing data.
3. Record exact outputs in `EVAL_HANDOFF.md`.
4. List every file changed.
5. Commit with a descriptive message.
6. Do not merge into main yourself.

---

# Prompt C: Core Technical Member

You own the main worktree and the integration. Follow `LocalRecall_Codex_Master_Prompt.md` as the primary instruction. In addition:

- Keep the Python `LocalRecallFacade` protocol stable after the UI and evaluation worktrees begin.
- Use mock inference to unblock teammates.
- Merge only after each branch has tests and a handoff file.
- Resolve conflicts yourself; do not ask less-technical members to use Git.
- Establish the SSH localhost tunnel on the presenter laptop and give each friend a working local browser session (no SSH knowledge required). Explain that a webcam is required only on the browser machine; show both snapshot/upload fallback and optional stream.
- Give each member a five-minute explanation of their task.
- Preserve `manual-mvp` and create a final known-good tag before submission.
- Schedule two architecture teach-backs so every member can answer judge questions.
