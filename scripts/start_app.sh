#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python_bin="${LOCALRECALL_PYTHON:-$repo_root/.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
    printf 'Python environment not found: %s\nRun `make setup` first.\n' "$python_bin" >&2
    exit 1
fi
exec "$python_bin" -m app.ui.app --backend --host 127.0.0.1 --port 7860
