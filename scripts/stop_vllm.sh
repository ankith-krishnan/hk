#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/docker_access.sh"

container_name="${VLLM_CONTAINER_NAME:-localrecall-vllm}"
if ! docker_cmd container inspect "$container_name" >/dev/null 2>&1; then
    printf 'Container %s is not present.\n' "$container_name"
    exit 0
fi
status="$(docker_cmd inspect --format '{{.State.Status}}' "$container_name")"
if [[ "$status" == "running" ]]; then
    docker_cmd stop --time 30 "$container_name"
else
    printf 'Container %s is already %s.\n' "$container_name" "$status"
fi
