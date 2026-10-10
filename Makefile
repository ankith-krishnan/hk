.PHONY: preflight setup model-start model-smoke run test eval demo-bundle stop

preflight:
	./scripts/preflight.sh

setup:
	python3 -m venv .venv
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

eval:
	.venv/bin/python scripts/run_eval.py --mock

demo-bundle:
	./scripts/export_demo_bundle.sh

stop:
	./scripts/stop_vllm.sh
