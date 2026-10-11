# Backend A — local model and validated response

## Mission

Backend A owns LocalRecall’s local vision-model integration and the conversion of an untrusted model response into a validated event result.

The goal is a conservative, testable model boundary: the application may ask the local Qwen model to interpret a prepared BEFORE/AFTER composite, but model output must never be treated as fact until it has been parsed, schema-validated, checked against the supplied object and zone IDs, and assigned the appropriate confidence state.

Follow [`LocalRecall_Codex_Master_Prompt.md`](./LocalRecall_Codex_Master_Prompt.md) as the source of truth for product behavior and technical constraints.

## Owns

Backend A owns:

- The `VLMClient` abstraction and its real and deterministic mock implementations.
- OpenAI-compatible localhost communication with `nvidia/Qwen3.8-27B-NVFP4`.
- Multimodal request construction, image encoding, timeouts, latency measurement, and useful local errors.
- The event-extraction and repair prompts under `app/prompts/`.
- Parsing and conservative cleanup of model responses.
- Pydantic validation of the model’s event JSON.
- Validation that returned object and zone IDs were allowed in the request context.
- Event semantics such as valid move direction, confidence handling, and uncertain fallback.
- One repair attempt for malformed or invalid model output.
- Model-runtime smoke tests and model-related documentation.

Typical files:

```text
app/vlm_client.py
app/event_analyzer.py
app/schemas.py              # only model-result schemas and changes coordinated with Backend B
app/config.py               # only model settings and local-URL validation
app/prompts/event_extractor.txt
app/prompts/event_repair.txt
scripts/smoke_text.py
scripts/smoke_vision.py
tests/test_schemas.py       # model/event validation coverage
tests/test_event_pipeline_mock.py
```

Backend A may also contribute to `app/composite.py` when the model-facing composite contract requires it, but image composition changes must preserve the shared interface used by Backend B and the frontends.

## Does not own

Backend A does not own:

- SQLite schema, event persistence, object state, query answers, deletion, export, or evidence cleanup.
- Saving object locations or changing current state directly.
- The facade contract or UI/backend contract without coordinating with Backend B.
- Browser-camera ingestion, the frame ring, source leases, motion state machine, or Watch Mode lifecycle.
- Gradio layout, callbacks, timers, or browser-camera controls.
- Model startup ownership beyond the agreed serving scripts and smoke-test expectations.
- Cloud inference, external APIs, or any non-local model endpoint.

Backend A returns a validated result to the caller. Backend B decides whether that result is accepted, queued for review, rejected, persisted, or used to rebuild object state.

## Required model contract

Keep all model access behind a small interface equivalent to:

```python
class VLMClient(Protocol):
    async def analyze_event(
        self,
        composite_path: Path,
        context: EventContext,
    ) -> VLMEventResult: ...

    async def answer_from_records(
        self,
        question: str,
        records: list[dict],
    ) -> str: ...
```

The model client must support:

- A real OpenAI-compatible HTTP client using `httpx`.
- A deterministic mock client that requires no model, camera, network, or database setup.
- Local image-to-data-URL conversion.
- Temperature `0` and a maximum output of 512 tokens for event extraction.
- Configurable timeout, with a useful error when the local endpoint is unavailable.
- Raw-response diagnostics that do not log secrets or unnecessary image data.
- Optional disabled thinking/reasoning parameters only when supported by the tested runtime.
- A local-only URL check when offline mode is enabled.

The application must remain usable in mock mode while Qwen is starting or unavailable.

## Event result schema

The model must return exactly one JSON object with this shape:

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

Validation requirements:

- `event_type` must be one of `move`, `appear`, `disappear`, `no_change`, or `uncertain`.
- `confidence` must be numeric and bounded from `0.0` through `1.0`.
- `object_id` must be `null` or one of the allowed registered IDs.
- Zone IDs must be `null`, `outside_view`, or one of the allowed zone IDs.
- A `move` must identify an object and two different source/destination locations.
- The result must not introduce an object, zone, destination, or fact absent from the supplied context.
- Evidence must be short, visible observations rather than speculation.
- Invalid, ambiguous, or insufficient output becomes `uncertain` with no state-changing interpretation.

Confidence policy:

```text
confidence >= 0.70       auto-accept candidate
0.45 <= confidence < .70 review candidate
confidence < 0.45        uncertain; no state mutation
```

Backend B owns the final persistence and acceptance decision, even when these thresholds are represented in shared configuration.

## Prompt behavior

`app/prompts/event_extractor.txt` must instruct the model to:

1. Compare only visible BEFORE and AFTER evidence.
2. Use only the supplied object and zone IDs.
3. Use `move` only when the same registered object clearly changes location.
4. Use `appear` and `disappear` only when the evidence supports them.
5. Use `no_change` when motion occurred but no registered object changed.
6. Use `uncertain` when the view is occluded, ambiguous, or insufficient.
7. Report at most one event, selecting the clearest event when several are visible.
8. Return JSON only, without Markdown or explanatory prose.

If the first response is malformed or fails validation, `event_repair.txt` may be used for exactly one repair request. If the repaired response still fails, return a safe uncertain result and do not mutate memory.

## Request and response flow

```text
Backend B / facade
        |
        | composite path + allowed IDs + context
        v
Backend A: VLMClient
        |
        | local multimodal request
        v
Qwen3.8-27B-NVFP4 on localhost
        |
        | raw response
        v
Backend A: parse -> validate -> ID checks -> semantic checks
        |
        | VLMEventResult + confidence/uncertainty metadata
        v
Backend B: accept/review/reject -> SQLite/state/evidence
```

The model endpoint is the only HTTP boundary required by the application. Do not add a REST API, WebSocket service, cloud API, or second inference service.

## Runtime and privacy constraints

- Use only `nvidia/Qwen3.8-27B-NVFP4` in the MVP.
- Keep the model endpoint on loopback, normally `http://127.0.0.1:8000/v1`.
- Reject non-local model URLs when `OFFLINE_MODE=1`.
- Do not download models or depend on external connectivity during normal operation.
- Do not write continuous video; the client receives the saved event composite selected by the pipeline.
- Do not retain model prompts or images beyond the project’s agreed evidence and diagnostic policy.
- Never attempt to open a server webcam. Browser frames and fixture images arrive through the shared backend pipeline.

Before the rest of the application depends on vision inference, run a text smoke test and a vision smoke test against the actual local runtime. Record real status, latency, and limitations; never invent model accuracy or performance.

## Testing requirements

Backend A must provide tests for:

- Valid event JSON parsing.
- Markdown code-fence cleanup.
- Missing fields, wrong types, invalid event types, and out-of-range confidence.
- Unknown object IDs and zone IDs.
- Invalid same-zone moves.
- Repair success after one malformed response.
- Safe uncertain fallback after two failures.
- Mock inference without Qwen, a camera, or network access.
- Local URL enforcement in offline mode.
- Real-client timeout and malformed-response errors where practical.
- Image request construction and accepted multimodal response parsing.

The complete repository test command must remain independent of the real model:

```bash
make test
```

Model-dependent checks may be run separately with:

```bash
make model-smoke
```

## Coordination rules

Coordinate with Backend B before changing:

- `VLMEventResult`, `EventContext`, `EventRecord`, or shared Pydantic schemas.
- The facade method signatures.
- The event acceptance thresholds.
- Composite layout, allowed-ID formatting, or evidence paths.
- Any SQLite-facing behavior or the meaning of accepted/review/uncertain events.

Coordinate with Frontend A and Frontend B before changing any displayed model status, error shape, evidence field, or callback return value. UI code must call the facade and must not import Backend A internals directly.

The naming note is important: the team-task document’s “Prompt B” means the evaluation/demo role. It is not Backend B and not Frontend B.

## Definition of done

Backend A is complete when:

- The real and mock `VLMClient` implementations satisfy the shared contract.
- The local Qwen text and vision paths have been smoke-tested, or the limitation is explicitly documented with the agreed fallback.
- Every model result passes schema, allowed-ID, and semantic validation before leaving Backend A.
- Exactly one repair attempt is made for invalid output.
- Invalid or ambiguous output produces an uncertain result without state mutation.
- Model latency, failures, and endpoint health are observable through the shared backend status path.
- Backend B can consume the result without knowing HTTP, prompt, or model internals.
- Tests pass in mock mode and all changed files are documented in the handoff.

## Handoff

Record:

- Changed files and shared-contract changes.
- Commands run and exact test results.
- Model image/checkpoint availability and the tested endpoint.
- Text and vision smoke-test status, latency, and known caveats.
- Any unresolved schema, prompt, composite, or facade coordination item.

Do not claim the model is working merely because the client imports successfully; show the actual smoke-test result or clearly mark it as unverified.
