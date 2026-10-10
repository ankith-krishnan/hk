# LocalRecall — private visual memory for your workspace

**Tagline:** Remember where things were, with local inference and evidence you can inspect.

## Inspiration

People lose time searching for everyday items. A camera could help, but sending room imagery to a cloud service creates a privacy cost. LocalRecall explores event-based memory for one intentionally bounded workspace.

## What it does

The current manual workflow compares a BEFORE and AFTER image, asks a local vision-language model for a constrained event record, validates that record against enrolled objects and zones, and stores accepted facts and evidence in SQLite. Users can ask deterministic questions such as where an object was last observed and open the supporting image pair. Low-confidence events can be reviewed or corrected.

## How it was built

The UI uses Gradio Blocks and an in-process Python facade. A `VLMClient` boundary targets a local OpenAI-compatible vLLM endpoint serving `nvidia/Qwen3.8-27B-NVFP4`; SQLite stores the event log and rebuildable object-state projection. The laptop browser owns the camera. Its frames cross the private laptop-to-GB10 connection; the server does not need a camera. The current stream is ingress-only while automatic motion analysis remains disabled.

## Why local AI matters

The design keeps image inference on the GB10 and avoids a cloud camera API. This supports local operation and user-controlled retention. It does not claim that the browser-to-server LAN traffic or Gradio's transient upload cache is nonexistent.

## Architecture

Browser upload/snapshot → Gradio → Python facade → labeled pair composite → loopback VLM client → validated event → SQLite event/evidence → evidence-backed query. See `ARCHITECTURE.md` and `RUNBOOK.md`.

## Challenges

The GB10 environment and Docker socket authorization must be verified before a model result can be demonstrated. Image support in the chosen serving recipe is a separate gate from text serving. A conservative event schema, confidence review, bounded browser input, transient-file cleanup, and truthful fallback are part of the MVP.

## Accomplishments so far

- Implemented a mock-backed manual image-pair pipeline, SQLite memory, evidence views, and five-tab UI.
- Added deterministic mock integration tests and a 20-trial synthetic evaluation harness.
- Recorded the actual GB10 host preflight and built a Docker launcher that validates image flags before use.
- Real Qwen inference and WAN-off operation remain unverified and must not be claimed until tested.

## Lessons learned

Treat text and image support as separate model gates. Keep the manual path independent of streaming. Preserve visible evidence and correctable events rather than treating model prose as memory. Measure temporary file behavior before making privacy claims.

## Limitations and future work

This is a prototype for a fixed desk, enrolled objects, and named zones. It is not universal object recognition, production-ready surveillance, or a continuously recording camera. Occlusion, lighting changes, camera movement, and similar objects can cause errors. Next: pass local Qwen image inference, complete real recorded trials, then implement an event-triggered motion gate with the browser frame ring.

## Setup

See `RUNBOOK.md`. The quick path is `make setup`, `make test`, and `python -m app.ui.app --mock`. Backend/model operation requires Docker access, the Qwen checkpoint, and successful real text and image smoke tests.

## Team contributions

Fill in actual names and contribution details before submission. Suggested roles from the demo plan: problem/privacy framing, product interaction and trial capture, and local model/backend/evaluation. Do not attribute work without confirming the team’s actual contributions.
