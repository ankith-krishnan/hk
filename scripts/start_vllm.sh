#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/docker_access.sh"

image="${VLLM_IMAGE:-vllm/vllm-openai:qwen38}"
container_name="${VLLM_CONTAINER_NAME:-localrecall-vllm}"
model="${VLLM_MODEL:-nvidia/Qwen3.8-27B-NVFP4}"
model_volume="${VLLM_MODEL_VOLUME:-localrecall-qwen38-cache}"
ready_timeout="${VLLM_READY_TIMEOUT_SECONDS:-900}"

die() { printf 'start_vllm: %s\n' "$*" >&2; exit 1; }

docker_cmd info >/dev/null 2>&1 || die 'Docker daemon is not accessible to this user.'
if ! docker_cmd image inspect "$image" >/dev/null 2>&1; then
    printf 'Pulling vLLM image %s\n' "$image"
    docker_cmd pull "$image"
fi

printf 'Image entrypoint and default command:\n'
docker_cmd image inspect --format 'Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}' "$image"

docker_cmd volume create "$model_volume" >/dev/null
printf 'Ensuring model %s exists in Docker volume %s (first run downloads the checkpoint).\n' "$model" "$model_volume"
docker_cmd run --rm -i \
    --volume "$model_volume:/root/.cache/huggingface/hub" \
    --entrypoint python3 \
    "$image" - "$model" <<'PY' || die 'Could not download or validate the model in the Docker volume.'
import json
import pathlib
import sys

from huggingface_hub import snapshot_download

repo_id = sys.argv[1]
cache = pathlib.Path("/root/.cache/huggingface/hub")
snapshot = pathlib.Path(snapshot_download(repo_id=repo_id, cache_dir=str(cache)))
required = (snapshot / "config.json", snapshot / "model.safetensors.index.json")
if any(not path.is_file() for path in required):
    raise SystemExit(f"incomplete model snapshot: {snapshot}")
index = json.loads(required[1].read_text())
shards = set(index.get("weight_map", {}).values())
missing = sorted(name for name in shards if not (snapshot / name).is_file())
if not shards or missing:
    raise SystemExit(f"missing model shards: {missing[:8]}")
print(f"Validated {repo_id} at {snapshot}; {len(shards)} weight shards are present.")
PY

help_file="$(mktemp)"
trap 'rm -f "$help_file"' EXIT
docker_cmd run --rm --entrypoint vllm "$image" serve --help >"$help_file" 2>&1 || {
    cat "$help_file" >&2
    die 'Could not inspect `vllm serve --help` in the selected image.'
}

required_flags=(
    --host
    --port
    --tensor-parallel-size
    --max-model-len
    --kv-cache-dtype
    --gpu-memory-utilization
    --max-num-seqs
    --max-num-batched-tokens
    --enable-chunked-prefill
    --reasoning-parser
)
for flag in "${required_flags[@]}"; do
    grep -Fq -- "$flag" "$help_file" || die "Selected image does not support required flag $flag; inspect its help before changing launch settings."
done
printf 'Validated launch flags against vLLM image help.\n'

if docker_cmd container inspect "$container_name" >/dev/null 2>&1; then
    state="$(docker_cmd inspect --format '{{.State.Status}}' "$container_name")"
    if [[ "$state" == "running" ]]; then
        printf 'Container %s is already running; checking readiness.\n' "$container_name"
        VLLM_READY_TIMEOUT_SECONDS="$ready_timeout" ./scripts/wait_for_vllm.sh
        exit $?
    fi
    die "Container $container_name already exists in state $state. Inspect it or remove it intentionally before retrying; this script will not discard it."
fi

docker_cmd run --detach \
    --name "$container_name" \
    --gpus all \
    --ipc host \
    --network host \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    --volume "$model_volume:/root/.cache/huggingface/hub:ro" \
    --env HF_HUB_OFFLINE=1 \
    --env TRANSFORMERS_OFFLINE=1 \
    --entrypoint vllm \
    "$image" \
    serve "$model" \
    --host 127.0.0.1 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --max-model-len 32768 \
    --kv-cache-dtype fp8 \
    --gpu-memory-utilization 0.75 \
    --max-num-seqs 4 \
    --max-num-batched-tokens 8192 \
    --enable-chunked-prefill \
    --reasoning-parser qwen3

VLLM_READY_TIMEOUT_SECONDS="$ready_timeout" ./scripts/wait_for_vllm.sh
