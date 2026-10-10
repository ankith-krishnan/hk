#!/usr/bin/env bash
set -u
source "$(dirname "${BASH_SOURCE[0]}")/docker_access.sh"

base_url="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
timeout_seconds="${VLLM_READY_TIMEOUT_SECONDS:-600}"
container_name="${VLLM_CONTAINER_NAME:-localrecall-vllm}"
health_url="${base_url%/v1}/health"
models_url="${base_url%/}/models"
deadline=$((SECONDS + timeout_seconds))

while (( SECONDS < deadline )); do
    health_code="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 3 "$health_url" 2>/dev/null || true)"
    if [[ "$health_code" == "200" ]]; then
        models_body="$(curl --silent --show-error --max-time 5 "$models_url" 2>/dev/null || true)"
        if [[ -n "$models_body" ]] && printf '%s' "$models_body" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("data")' >/dev/null 2>&1; then
            printf 'vLLM ready: %s\n' "$models_body"
            exit 0
        fi
    fi
    sleep 2
done

printf 'Timed out waiting for vLLM at %s after %ss.\n' "$health_url" "$timeout_seconds" >&2
if command -v docker >/dev/null 2>&1; then
    printf 'Last logs from %s:\n' "$container_name" >&2
    docker_cmd logs --tail 100 "$container_name" >&2 || true
fi
exit 1
