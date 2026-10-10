# LocalRecall

LocalRecall is a planned private visual-memory appliance for one bounded tabletop workspace. It records semantic object events and evidence so a user can ask where an enrolled object was last seen, without sending image inference to a cloud service or retaining continuous application video.

The authoritative implementation requirements are in [LocalRecall_Codex_Master_Prompt.md](LocalRecall_Codex_Master_Prompt.md), [LocalRecall_Implementation_Blueprint.md](LocalRecall_Implementation_Blueprint.md), [LocalRecall_Team_Task_Prompts.md](LocalRecall_Team_Task_Prompts.md), and [HEADLESS_CAMERA_RUNBOOK.md](HEADLESS_CAMERA_RUNBOOK.md). Those documents define the architecture. This README summarizes them and reports implementation state; it does not replace their decisions.

## Product flow

The first acceptance path is manual: provide separate BEFORE and AFTER images in the browser, analyze the pair with a local vision-language model, validate the structured result, store event evidence and accepted state in SQLite, then answer a query from those records. This path must work without a camera or a streaming session.

Optional Watch Mode comes later. The presenter laptop browser owns the webcam and sends sampled frames to the headless GB10 over a private connection. OpenCV detects scene changes from those browser-supplied frames. The system retains a bounded in-memory ring, selects stable BEFORE and AFTER images, and sends a labeled composite to the local model only after a candidate event. The GB10 itself does not need a camera.

```text
Laptop browser (webcam snapshots, uploads, optional stream)
             |
             | SSH local port forward over private LAN
             v
Gradio Blocks on GB10 localhost:7860
             |
             +--> Python facade --> OpenCV / zones / composites
             |                         |
             |                         v
             |              local vLLM endpoint :8000
             |                         |
             +--> SQLite event log <-- validated event JSON
                         |
                         +--> evidence-backed answers
```

The guiding separation is: OpenCV decides when a scene may have changed, the VLM describes visible evidence, and SQLite owns factual memory. The model is `nvidia/Qwen3.8-27B-NVFP4`, a mixed NVFP4/FP8 multimodal checkpoint. The preferred serving path is the Spark-specific Docker image `vllm/vllm-openai:qwen38`; image inference must be proven before the rest of the application depends on it.

## Scope and privacy

- Three default zones and a small registry of three to five named objects.
- One event at a time, with confidence-based acceptance or review.
- Event evidence and registered-object references may be retained; continuous application video is not written by default.
- Browser uploads and webcam frames travel over the local laptop-to-GB10 connection. A localhost SSH forward gives the laptop browser a camera-permitted origin; frames do cross that local connection.
- Gradio may create temporary image cache files. The implementation must use and document a dedicated temporary directory and cleanup behavior, and must not claim that no transient files exist without measuring it.
- Model requests stay on loopback; no cloud inference APIs, public Gradio sharing, external database, or second web API are part of the design.
- For an offline demo, disable external WAN access while keeping the laptop-to-GB10 LAN/SSH link active.

## Requirements and intended commands

The target is Ubuntu 24.04 on an NVIDIA GB10-class system, Python 3.11 or 3.12, Docker with NVIDIA Container Toolkit, and the local Qwen checkpoint. The organizer-provided ASUS Ascent GX10 is the judging target; a personal development Spark is not a substitute.

The intended model commands are:

```bash
./scripts/start_vllm.sh
./scripts/wait_for_vllm.sh
python scripts/smoke_text.py
python scripts/smoke_vision.py
```

The intended app commands, after implementation, are:

```bash
python -m app.ui.app --mock --port 7861
python -m app.ui.app --backend --host 127.0.0.1 --port 7860
```

On the presenter laptop, forward the app port and browse to localhost:

```bash
ssh -N -L 7860:127.0.0.1:7860 <spark-user>@<spark-lan-ip>
```

Then open `http://127.0.0.1:7860` on that laptop and allow camera access if using webcam inputs. File uploads remain the fallback. These are target commands, not a claim that the scripts or app are already available; see [STATUS.md](STATUS.md) for verified progress.

## Current implementation status

The environment preflight is complete and recorded in [STATUS.md](STATUS.md). The manual mock-backed facade, SQLite memory, composite builder, event validation, browser frame ingress, and five-tab Gradio UI are implemented. The mock-mode UI returns HTTP 200 and exposes all five tabs; the automated suite currently passes. The Qwen checkpoint download is active. Docker daemon access is still denied, so the container launch flags remain unverified and no real vLLM, text, or image inference result is claimed.

## Limitations

The intended MVP is a fixed, bounded workspace with enrolled objects and named zones. It is not general room surveillance or unconstrained object tracking. Occlusion, ambiguous identities, changed camera placement, lighting, and mirrored webcam images can reduce reliability. Low-confidence and invalid model outputs must not silently mutate object state. Manual BEFORE/AFTER analysis remains a first-class fallback if streaming is unavailable or unreliable.
