# Evaluation work plan

1. Add a JSONL ground-truth schema with at least 20 trials, four objects, and three zones.
2. Generate deterministic BEFORE/AFTER pairs plus optional stable/move/no-change videos; keep generated media out of Git.
3. Run each pair through `EventAnalyzer` using either the deterministic mock or configured loopback VLM.
4. Save raw response, prediction, timing, and per-trial ground truth as JSON; render a Markdown report.
5. Run mock evaluation and tests; report only measured mock-harness values. Real performance remains unavailable until local Qwen has passed image inference.
6. Add a repeatable demo archive and record exact gate status in `EVAL_HANDOFF.md`.

## Current scope

The current manifest contains 20 synthetic trials: clear moves, no-change hand passes and stable scenes, appearances, disappearances, and two ambiguous cases. Generated image pairs and optional videos live in ignored `data/evaluation/generated/`. No recorded real-world trials or Qwen evaluation are available yet.
