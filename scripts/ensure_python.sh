#!/usr/bin/env bash
# LocalRecall requires Python >=3.11,<3.13 (see pyproject.toml requires-python).
set -euo pipefail

python_minor() {
  "$1" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null
}

python_version_line() {
  "$1" --version 2>&1 | head -n1
}

is_supported_minor() {
  local minor="$1"
  [[ "$minor" == "11" || "$minor" == "12" ]]
}

validate_python() {
  local py="$1"
  [[ -n "$py" && -x "$py" ]] || return 1
  local minor
  minor="$(python_minor "$py" || echo 99)"
  is_supported_minor "$minor"
}

unsupported_message() {
  local py="$1"
  local minor="$2"
  local version_line
  version_line="$(python_version_line "$py")"
  if [[ "$minor" -lt 11 ]]; then
    cat >&2 <<EOF
${version_line} is too old for LocalRecall (requires Python >=3.11,<3.13 per pyproject.toml).

Install Python 3.12 or 3.11, then re-run make setup (see instructions below).
EOF
  else
    cat >&2 <<EOF
${version_line} is not supported (LocalRecall requires Python >=3.11,<3.13 per pyproject.toml).

Use Python 3.12 or 3.11 — for example a dedicated conda env — then re-run make setup.
EOF
  fi
  cat >&2 <<'EOF'

Install Python 3.12, then re-run make setup:

  Option A — python.org (recommended on Mac)
    Download and install Python 3.12 from https://www.python.org/downloads/
    Ensure /Library/Frameworks/Python.framework/Versions/3.12/bin is on your PATH.

  Option B — conda
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    conda create -y -n localrecall python=3.12
    conda activate localrecall

Then from the repo:
    make setup
EOF
}

pick_python() {
  if [[ -n "${LOCALRECALL_PYTHON:-}" ]]; then
    echo "${LOCALRECALL_PYTHON}"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo python
    return 0
  fi
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

PY="$(pick_python || true)"
if [[ -z "${PY}" ]]; then
  cat >&2 <<'EOF'
No Python interpreter found on PATH.

Install Python 3.12, then re-run make setup:

  Option A — python.org (recommended on Mac)
    Download and install Python 3.12 from https://www.python.org/downloads/
    Ensure /Library/Frameworks/Python.framework/Versions/3.12/bin is on your PATH.

  Option B — conda
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    conda create -y -n localrecall python=3.12
    conda activate localrecall

Then from the repo:
    make setup
EOF
  exit 1
fi

if ! command -v "$PY" >/dev/null 2>&1 && [[ ! -x "$PY" ]]; then
  cat >&2 <<EOF
LOCALRECALL_PYTHON or selected interpreter is not executable: ${PY}
EOF
  exit 1
fi

minor="$(python_minor "$PY" || echo 99)"
if ! is_supported_minor "$minor"; then
  unsupported_message "$PY" "$minor"
  exit 1
fi

echo "$PY"
