#!/usr/bin/env bash
set -euo pipefail

image="${VLLM_IMAGE:-vllm/vllm-openai:qwen38}"
container_name="${VLLM_CONTAINER_NAME:-localrecall-vllm}"
model="${VLLM_MODEL:-nvidia/Qwen3.8-27B-NVFP4}"
cache_dir="${HF_HUB_CACHE:-$HOME/.cache/huggingface/hub}"
ready_timeout="${VLLM_READY_TIMEOUT_SECONDS:-900}"

die() { printf 'start_vllm: %s\n' "$*" >&2; exit 1; }

docker info >/dev/null 2>&1 || die 'Docker daemon is not accessible to this user.'
[[ -d "$cache_dir" ]] || die "Hugging Face cache directory does not exist: $cache_dir"

model_snapshot="$(find "$cache_dir/models--nvidia--Qwen3.8-27B-NVFP4/snapshots" -mindepth 1 -maxdepth 1 -type d -print -quit 2>/dev/null || true)"
[[ -n "$model_snapshot" ]] || die "Model $model was not found in $cache_dir; complete the HF download first."
[[ -f "$model_snapshot/config.json" && -f "$model_snapshot/model.safetensors.index.json" ]] || \
    die "Model snapshot is incomplete: expected config.json and model.safetensors.index.json in $model_snapshot"
python3 - "$model_snapshot" <<'PY' || die 'Model snapshot is missing one or more weight shards.'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
index = json.loads((root / "model.safetensors.index.json").read_text())
files = set(index.get("weight_map", {}).values())
if not files or any(not (root / filename).is_file() for filename in files):
    raise SystemExit(1)
PY

if ! docker image inspect "$image" >/dev/null 2>&1; then
    printf 'Pulling vLLM image %s\n' "$image"
    docker pull "$image"
fi

printf 'Image entrypoint and default command:\n'
docker image inspect --format 'Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}' "$image"
help_file="$(mktemp)"
trap 'rm -f "$help_file"' EXIT
docker run --rm --entrypoint vllm "$image" serve --help >"$help_file" 2>&1 || {
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

if docker container inspect "$container_name" >/dev/null 2>&1; then
    state="$(docker inspect --format '{{.State.Status}}' "$container_name")"
    if [[ "$state" == "running" ]]; then
        printf 'Container %s is already running; checking readiness.\n' "$container_name"
        VLLM_READY_TIMEOUT_SECONDS="$ready_timeout" ./scripts/wait_for_vllm.sh
        exit $?
    fi
    die "Container $container_name already exists in state $state. Inspect it or remove it intentionally before retrying; this script will not discard it."
fi

docker run --detach \
    --name "$container_name" \
    --gpus all \
    --ipc host \
    --network host \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    --volume "$cache_dir:/root/.cache/huggingface/hub:ro" \
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
