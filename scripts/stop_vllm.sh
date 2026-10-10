#!/usr/bin/env bash
set -euo pipefail

container_name="${VLLM_CONTAINER_NAME:-localrecall-vllm}"
if ! docker container inspect "$container_name" >/dev/null 2>&1; then
    printf 'Container %s is not present.\n' "$container_name"
    exit 0
fi
status="$(docker inspect --format '{{.State.Status}}' "$container_name")"
if [[ "$status" == "running" ]]; then
    docker stop --time 30 "$container_name"
else
    printf 'Container %s is already %s.\n' "$container_name" "$status"
fi
