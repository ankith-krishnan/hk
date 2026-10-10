# LocalRecall  
**A private, event-sourced visual memory that remembers where objects were placed without storing continuous video or sending frames to the cloud.**

The project uses `nvidia/Qwen3.8-27B-NVFP4` as the only foundation model in the critical path. NVIDIA’s model card lists text, image, and video input support, and says the checkpoint uses NVFP4 for its MLP and language-head layers with FP8 for attention-related layers. The GB10 has Blackwell Tensor Cores with native FP4 support, so your instinct to prioritize the NVFP4 checkpoint is correct. [Hugging Face](https://huggingface.co/nvidia/Qwen3.8-27B-NVFP4)

I created three files:

1. **Give this directly to the primary Codex agent.** It tells Codex to inspect the machine, build the repository, run the model, implement the system, test it, maintain status, and preserve fallbacks.

   :chatgpt-content-reference{index="8"}[Download the Codex master prompt](sandbox:/mnt/data/LocalRecall_Codex_Master_Prompt.md)

2. **This is the complete human-readable technical blueprint.** It covers architecture, database schema, APIs, motion detection, prompting, UI, privacy, evaluation, judging, time gates, and acceptance criteria.

   :chatgpt-content-reference{index="9"}[Download the full implementation blueprint](sandbox:/mnt/data/LocalRecall_Implementation_Blueprint.md)

3. **These are bounded prompts for your two less-technical teammates.** One owns the UI through Codex; the other owns evaluation, demo preparation, Devpost, and presentation material.

   :chatgpt-content-reference{index="10"}[Download the team task prompts](sandbox:/mnt/data/LocalRecall_Team_Task_Prompts.md)

## The core architecture

Do **not** run the 27B VLM continuously on webcam frames. That would be slower, harder to debug, and unnecessary.

Use this:

```text
USB webcam
    |
    v
OpenCV capture thread
    |
    v
Cheap motion detection
    |
    +---- no meaningful change ----> discard
    |
    v
Clean BEFORE and AFTER frames
    |
    v
Labeled comparison image
- BEFORE and AFTER
- named zone overlays
- enrolled-object reference images
    |
    v
Qwen3.8-27B-NVFP4 on the local GB10
    |
    v
Strict JSON event
    |
    v
Validation and confidence policy
    |
    v
SQLite event log and current object state
    |
    v
Local web UI
- live view
- object enrollment
- visual timeline
- natural-language questions
- evidence
- privacy controls
```

The important product concept is:

> **Classical vision decides when something changed. The VLM decides what changed. SQLite decides what is true.**

That separation is what makes the project defensible.

## The exact demo

Set up a fixed workspace with three labeled areas:

- Left Tray
- Center Mat
- Right Tray

Enroll three visibly distinct objects:

- keys,
- wallet,
- red mug.

Then demonstrate:

1. The system is in Watch Mode.
2. Move the keys from Left Tray to Right Tray.
3. The UI changes from `Stable` to `Motion`, `Settling`, and `Analyzing`.
4. An event appears:

```text
Keys moved
Left Tray -> Right Tray
Confidence: 91%
```

5. Ask:

```text
Where are my keys?
```

6. The answer says:

```text
Your keys were last observed in the Right Tray at 3:24 PM.
Evidence: Event #12
```

7. Open the BEFORE/AFTER evidence.
8. Disconnect external internet access.
9. Repeat the query.
10. Open the privacy page and show:
   - local model,
   - no cloud endpoint,
   - no continuous video stored,
   - only event evidence retained,
   - Delete All Memory button.

That directly addresses ASUS’s requirements to solve a real problem, show technical originality, and make the value of local AI explicit. The rules require development and demonstration on the GX10, but they do not require using Nemotron. Pasted text

## Why Qwen3.8 is the right primary model

Use:

```text
nvidia/Qwen3.8-27B-NVFP4
```

Do not use these in the critical path:

| Model | Decision |
|---|---|
| Qwen3.8-27B-NVFP4 | Primary visual and language model |
| Nemotron 3.5 Lightning BF16 | Drop; text-only and redundant |
| Alpamayo 1.5 10B | Drop; visually capable but automobile-specialized |
| Cosmos3-Nano | Drop; powerful but unnecessarily complex for this product |
| Flash Attention cache | Leave intact; use only as required by the chosen serving container |

NVIDIA’s current DGX Spark vLLM instructions specifically pair a single Spark with `vllm/vllm-openai:qwen38` and `nvidia/Qwen3.8-27B-NVFP4`, so this is not an invented hardware configuration. [NVIDIA NIM APIs](https://build.nvidia.com/spark/vllm/instructions?utm_source=chatgpt.com)

However, there is an important caveat: the general Qwen3.8 vLLM recipe says the architecture is multimodal, but notes that **text serving is the path that was verified in that recipe**. Therefore, image inference must be your first technical gate rather than something you assume will work later. [vLLM Recipes](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)

The master prompt enforces this sequence:

1. Load the model.
2. Run a text request.
3. Run a one-image request.
4. Run a synthetic BEFORE/AFTER image request.
5. Require parseable JSON.
6. Repeat in offline mode.
7. Only then build the rest of the product around it.

If vLLM text works but vision does not after 60–90 minutes of focused debugging, the plan switches to the Spark-supported SGLang path while retaining the same `VLMClient` application interface. NVIDIA documents SGLang on DGX Spark, including NVFP4 model handling and OpenAI-compatible endpoints. [NVIDIA NIM APIs](https://build.nvidia.com/spark/sglang/instructions.md?utm_source=chatgpt.com)

## Why the project is feasible

The system deliberately avoids four difficult problems:

- It does not recognize every object in a room.
- It does not process every video frame with a VLM.
- It does not infer where invisible objects went.
- It does not ask an LLM to be the factual database.

Instead:

- The user enrolls three to five objects.
- The user defines three to four zones.
- The camera is fixed.
- Only one clear object movement is expected per event.
- OpenCV chooses clean frames after the person’s hand leaves.
- The VLM receives one carefully labeled comparison image.
- Invalid or low-confidence model results do not update memory.
- A manual BEFORE/AFTER capture mode always remains available.

That manual mode is crucial. Even if automatic motion thresholds are imperfect, your actual visual-memory pipeline can still be demonstrated reliably.

## Event format

The model must return something like:

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

The application then performs deterministic validation:

- Is `keys` a registered object?
- Are both zones registered?
- Are the source and destination different?
- Is the output valid JSON?
- Is confidence above the acceptance threshold?

Recommended policy:

```text
>= 0.70       automatically accept
0.45 - 0.69   place in review queue
< 0.45        mark uncertain; do not update location
```

This gives you a very strong answer when judges ask, “What happens when the model hallucinates?”

## Database design

Use SQLite in WAL mode with these tables:

```text
objects
zones
events
object_state
queries
metrics
settings
```

The `events` table is append-only historical memory.

The `object_state` table is a derived current view:

```text
keys -> right_tray -> event #12
wallet -> center_mat -> event #9
mug -> left_tray -> event #10
```

The model never directly answers “where are the keys?” from its conversation history. The application retrieves the last accepted database event, then presents that result and its evidence.

This is safer, easier to test, and more technically credible than treating an LLM chat context as memory.

## Team division without requiring your friends to know SSH

### You: technical architect and integration owner

You own:

- vLLM/SGLang runtime,
- Qwen multimodal smoke test,
- VLM client,
- event schema,
- database behavior,
- motion detection,
- integration,
- difficult debugging.

### Friend 1: product experience owner

Their Codex worktree may edit only:

```text
app/static/**
```

They guide Codex to build:

- Live page,
- object cards,
- visual event timeline,
- Ask page,
- Privacy page,
- loading states,
- error handling,
- visual polish.

They can do this by inspecting the application in a browser and telling Codex what to change. No SSH knowledge is necessary.

### Friend 2: evaluation and demo owner

Their Codex worktree owns:

```text
scripts/run_eval.py
tests/fixtures/**
DEMO_SCRIPT.md
DEVPOST_DRAFT.md
PITCH_QA.md
```

They:

- define the 20-trial test matrix,
- enroll and move objects,
- record correct/incorrect outcomes,
- calculate honest metrics,
- write the pitch,
- make the backup demo,
- prepare Devpost content.

This is real work, not fake busywork. It directly supports the judging criteria.

After the initial scaffold commit, Codex can create separate branches and worktrees:

```bash
git worktree add ../localrecall-ui -b feature/ui
git worktree add ../localrecall-eval -b feature/eval
```

Open a separate Codex thread in each folder. Your friends interact with those threads and browser results; you handle merging.

The hackathon guide explicitly says every team member must be able to explain how the project works, so the plan includes two short architecture teach-backs rather than allowing the others to remain disconnected from the implementation. Pasted text

## Execution schedule

The event starts hacking at noon Saturday, the venue closes at 10:00 PM, reopens at 9:00 AM Sunday, and submissions are due at 1:30 PM. Pasted text

### Saturday

**12:00–12:45 — model gate**

- Run hardware preflight.
- Locate the existing model cache.
- Start `vllm/vllm-openai:qwen38`.
- Pass text test.
- Pass image test.
- Pass strict JSON change-analysis test.

**12:45–2:15 — manual vertical slice**

By 2:15, this must work:

```text
Manual BEFORE
-> Manual AFTER
-> Qwen analysis
-> valid event JSON
-> SQLite
-> "Where are my keys?"
-> evidence
```

Nothing else is more important.

**2:15–4:00 — camera and automatic detection**

- Camera thread.
- Motion state machine.
- Stable-frame selection.
- Default zones.
- Fixture-video mode.

**4:00–5:30 — enrollment and UI**

- Three object references.
- Zone editor.
- Live state indicators.
- Memory timeline.
- Ask interface.

**5:30–7:00 — real trials**

- Move real objects.
- Tune thresholds.
- Improve the event prompt.
- Add review behavior.
- Measure actual latency.

**7:00–8:30 — evaluation and offline proof**

- Run trial matrix.
- Restart in offline mode.
- Verify continuous-video storage is zero.
- Finish privacy page.
- Draft Devpost.

**8:30–9:20 — demo hardening**

- Record backup demo.
- Rehearse.
- Take screenshots.
- Stop adding features.

**9:20–9:45 — freeze**

- Tag known-good commit.
- Export source and assets.
- Back up database and video.
- Leave with something bootable.

### Sunday

**9:00–10:00**

- Cold-boot test.
- Start model from script.
- Start application.
- Run full demo.

**10:00–11:30**

- Finish measured evaluation.
- Finalize pitch and Q&A.

**11:30–12:30**

- Complete Devpost.
- Upload screenshots and backup video.
- Verify repository setup instructions.

**12:30–1:00**

- Freeze submission.
- Table setup.
- Full-team rehearsal.

Do not plan to submit at 1:29 PM.

## What to give Codex first

Place the three downloaded Markdown files in the repository root. Then open the primary Codex agent in that repository and paste the contents of:

:chatgpt-content-reference{index="11"}[LocalRecall_Codex_Master_Prompt.md](sandbox:/mnt/data/LocalRecall_Codex_Master_Prompt.md)

Do not launch the teammate worktrees immediately. Let the primary agent complete:

```text
environment preflight
model text smoke test
model vision smoke test
manual end-to-end MVP
initial commit and manual-mvp tag
```

Only after that should you create the UI and evaluation worktrees and give your friends their prompts.

The most important rule is:

> **Do not let Codex spend the afternoon building a beautiful UI before the Qwen image request and manual BEFORE/AFTER pipeline work.**

The plan is intentionally designed so that, even under failure, you still finish with a credible local visual-memory demonstration rather than an ambitious collection of disconnected components.
