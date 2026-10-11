#!/usr/bin/env bash
# LocalRecall needs Python 3.11 or 3.12 (Gradio + pinned pydantic do not support 3.14 yet).
set -euo pipefail

pick_python() {
  if [[ -n "${LOCALRECALL_PYTHON:-}" && -x "${LOCALRECALL_PYTHON}" ]]; then
    echo "${LOCALRECALL_PYTHON}"
    return 0
  fi
  # Prefer the active conda/venv interpreter when it is already 3.11 or 3.12.
  if command -v python >/dev/null 2>&1; then
    minor="$(python -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 99)"
    if [[ "$minor" == "11" || "$minor" == "12" ]]; then
      echo python
      return 0
    fi
  fi
  for candidate in python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  if command -v python3 >/dev/null 2>&1; then
    echo python3
    return 0
  fi
  return 1
}

PY="$(pick_python || true)"
if [[ -z "${PY}" ]]; then
  cat >&2 <<'EOF'
No Python interpreter found.

Install Python 3.12, then re-run make setup:

  Option A — python.org (recommended on Mac)
    Download and install Python 3.12 from https://www.python.org/downloads/
    Ensure /Library/Frameworks/Python.framework/Versions/3.12/bin is on your PATH.

  Option B — conda (you already use base)
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    conda create -y -n localrecall python=3.12
    conda activate localrecall

Then from the repo:
    make setup
EOF
  exit 1
fi

minor="$("$PY" -c 'import sys; print(sys.version_info.minor)')"
if [[ "$minor" -ge 13 ]]; then
  cat >&2 <<EOF
$("$PY" --version) is too new for this project's pinned Gradio/pydantic stack.

Use Python 3.12 (see instructions above). Your default python3 is 3.14 from conda base —
activate a 3.12 env or install python3.12 before running make setup.
EOF
  exit 1
fi

echo "$PY"
