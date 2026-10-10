#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
python_bin="${PYTHON_BIN:-.venv/bin/python}"
app_url="${APP_URL:-http://127.0.0.1:7860}"

endpoint_file="$(mktemp)"
trap 'rm -f "$endpoint_file"' EXIT
"$python_bin" - "$app_url" >"$endpoint_file" <<'PY'
import sys
from urllib.parse import urlsplit

from app.config import Settings, is_loopback_url

settings = Settings()
app_url = sys.argv[1]
if not is_loopback_url(settings.vlm_base_url):
    raise SystemExit("FAIL: VLM_BASE_URL is not loopback")
if not is_loopback_url(app_url):
    raise SystemExit("FAIL: APP_URL must be localhost/loopback (use the SSH local forward from the laptop)")
print(f"PASS: model endpoint is loopback ({settings.vlm_base_url})")
print(f"PASS: browser app URL is loopback ({urlsplit(app_url).hostname})")
health_url = settings.vlm_base_url.rstrip("/").removesuffix("/v1")
print(health_url)
PY
mapfile -t endpoint_info <"$endpoint_file"
health_url="${endpoint_info[-1]}"
if ((${#endpoint_info[@]} > 1)); then
    printf '%s\n' "${endpoint_info[@]:0:${#endpoint_info[@]}-1}"
fi

curl --fail --silent --show-error --max-time 2 "$health_url/health" >/dev/null
curl --fail --silent --show-error --max-time 2 "${health_url}/v1/models" >/dev/null
curl --fail --silent --show-error --max-time 3 "${app_url%/}/" >/dev/null
printf 'PASS: local vLLM health/models and Gradio app answered.\n'
printf 'Cloud credential check: LocalRecall code uses the configured loopback VLM endpoint; this check does not inspect or print credential values.\n'
printf 'External WAN isolation is not inferred from these local checks. For that test, disable only WAN upstream access while preserving the laptop-to-GB10 LAN/SSH route, then run this command again. Do not alter host firewall rules automatically.\n'
