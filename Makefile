.PHONY: preflight setup model-start model-smoke run test lint eval demo-bundle offline-check stop

PYTHON ?= $(shell ./scripts/ensure_python.sh 2>/dev/null || true)

preflight:
	./scripts/preflight.sh

setup:
	@chmod +x scripts/ensure_python.sh
	@PY=$$(./scripts/ensure_python.sh); echo "Using $$PY"; \
	$$PY -m venv .venv; \
	.venv/bin/python -m pip install -U pip; \
	.venv/bin/python -m pip install -e '.[dev]'

model-start:
	./scripts/start_vllm.sh

model-smoke:
	./scripts/wait_for_vllm.sh
	.venv/bin/python scripts/smoke_text.py
	.venv/bin/python scripts/smoke_vision.py

run:
	.venv/bin/python -m app.ui.app --backend --host 127.0.0.1 --port 7860

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/ruff check app scripts tests

eval:
	.venv/bin/python scripts/make_fixture_video.py --output-dir data/evaluation/generated --manifest tests/fixtures/trial_manifest.jsonl
	.venv/bin/python scripts/run_eval.py --mock

demo-bundle:
	./scripts/export_demo_bundle.sh

offline-check:
	./scripts/check_offline.sh

stop:
	./scripts/stop_vllm.sh
