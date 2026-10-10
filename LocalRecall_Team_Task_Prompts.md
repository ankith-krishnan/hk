# LocalRecall Team Task Prompts

These prompts assume the primary Codex agent has already scaffolded the repository and committed the manual MVP. Use Git worktrees so the three agents do not edit the same files.

---

# Setup by the technical member

Run once from the main repository after the initial scaffold commit:

```bash
git worktree add ../localrecall-ui -b feature/ui
git worktree add ../localrecall-eval -b feature/eval
```

Open three separate Codex threads or windows:

- Core agent at the main repository.
- UI agent at `../localrecall-ui`.
- Evaluation/demo agent at `../localrecall-eval`.

The two less-technical members should not need to use SSH or Git commands themselves. The technical member opens the correct folder, pastes the relevant prompt, and then lets that member guide the agent by reviewing visible results.

---

# Prompt A: Product Experience and UI Member

You are the product-experience implementation agent for LocalRecall. A separate core agent owns the backend and model integration. Your job is to make the existing application understandable, polished, and demo-ready without changing backend behavior.

## Path ownership

You may modify only:

```text
app/static/**
tests/test_static_assets.py
tests/test_frontend_contract.py
TASK_UI.md
UI_HANDOFF.md
```

Do not modify Python backend files, database code, model code, API paths, Makefile, or deployment scripts. If an API appears missing, document the needed contract in `UI_HANDOFF.md`; do not invent a competing backend.

## Read first

Read:

- `AGENTS.md`
- `README.md`
- `ARCHITECTURE.md`
- current OpenAPI schema from the running app if available
- all files under `app/static/`

Write a short plan into `TASK_UI.md` before editing.

## Product goal

The interface should make this story obvious within ten seconds:

1. The camera is watching one workspace.
2. The system remembers object movements locally.
3. The user can ask where an object is.
4. Every answer has visible evidence.
5. Continuous video is not stored.

## Required tabs

Build or improve these tabs in one responsive single-page UI:

### Live

Show:

- live camera feed,
- zone overlays,
- large Watch Mode toggle,
- current state pill such as Stable, Motion, Settling, Analyzing, or Review,
- motion score,
- latest-event card,
- Manual Remember buttons for Capture BEFORE and Capture AFTER and Analyze.

### Objects

Show:

- enrolled objects,
- reference image,
- display name,
- aliases,
- enrollment controls,
- clear empty state.

### Zones

Show:

- current zone list,
- snapshot and canvas editor if the existing API supports it,
- Load Demo Layout button,
- delete controls,
- clear instructions.

### Memory

Show:

- chronological event cards,
- large BEFORE and AFTER thumbnails,
- object and movement summary,
- confidence,
- timestamp,
- accepted/review/uncertain status,
- evidence text,
- accept or correct controls when supported.

### Ask

Show:

- prominent question input,
- suggested questions,
- answer card,
- event references,
- evidence thumbnail.

### Privacy and System

Show:

- Local and Offline badge,
- model name,
- model and camera health,
- number of saved events and images,
- clear text saying continuous raw video is not retained,
- Delete All Memory with confirmation,
- latency summary and VLM call count when supplied by the API.

## Visual direction

Use a polished appliance aesthetic:

- dark or neutral background,
- strong readable typography,
- one restrained accent color,
- high contrast,
- large status indicators,
- rounded evidence cards,
- obvious BEFORE and AFTER labels,
- no excessive gradients or animation,
- no developer-looking JSON on the main screen.

Add a Technical Details disclosure rather than putting jargon everywhere.

## Reliability requirements

- Handle API errors visibly and politely.
- Never leave buttons stuck in loading state.
- Disable controls while a request is running.
- Show camera/model offline states clearly.
- Preserve the last visible successful event if WebSocket reconnects.
- Avoid external fonts, CDNs, analytics, and cloud assets.
- Everything must work offline.
- No console errors during the primary demo flow.

## Acceptance flow

Use the running backend or mock data and verify:

1. Open app.
2. See Live tab.
3. Load demo zones.
4. View enrolled objects.
5. Capture manual BEFORE.
6. Capture manual AFTER and analyze.
7. See event card.
8. Ask where the object is.
9. See answer and evidence.
10. Open Privacy tab.

Add narrow tests that verify required DOM IDs or data attributes used by the existing JavaScript. Do not add a Node build system.

## Handoff

When done:

1. Run the relevant tests.
2. Record exact results in `UI_HANDOFF.md`.
3. List every file changed.
4. List any backend API contract still needed.
5. Commit with a descriptive message.
6. Do not merge into main yourself.

---

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

Do not modify model-serving scripts, database implementation, motion implementation, API behavior, or UI files. If a required API is missing, document it in `EVAL_HANDOFF.md`.

## Read first

Read:

- `AGENTS.md`
- `README.md`
- `ARCHITECTURE.md`
- `RUNBOOK.md`
- existing API documentation
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
2. Submit each fixture through the existing application or event-analysis API.
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

Create a fallback version for use with a recorded demo if the camera fails.

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
- How do you prove it works offline?
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

- Keep API contracts stable after the UI and evaluation worktrees begin.
- Use mock inference to unblock teammates.
- Merge only after each branch has tests and a handoff file.
- Resolve conflicts yourself; do not ask less-technical members to use Git.
- Give each member a working browser URL and a five-minute explanation of their task.
- Preserve `manual-mvp` and create a final known-good tag before submission.
- Schedule two architecture teach-backs so every member can answer judge questions.
