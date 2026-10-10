#!/usr/bin/env bash
set -u
source "$(dirname "${BASH_SOURCE[0]}")/docker_access.sh"

printf '%s\n' '== LocalRecall environment preflight =='
printf '\n%s\n' '-- OS and architecture --'
uname -a
uname -m
cat /etc/os-release

printf '\n%s\n' '-- Python --'
python3 --version 2>&1 || true

printf '\n%s\n' '-- NVIDIA GPU --'
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi
else
    printf '%s\n' 'nvidia-smi unavailable'
fi

printf '\n%s\n' '-- Memory and storage --'
free -h 2>&1 || true
df -h . 2>&1 || true

printf '\n%s\n' '-- Docker --'
if command -v docker >/dev/null 2>&1; then
    docker --version
    if docker_cmd info >/dev/null 2>&1; then
        printf '%s\n' 'Docker daemon: accessible'
        docker_cmd info --format 'Server={{.ServerVersion}} Root={{.DockerRootDir}}'
        docker_cmd image ls
    else
        printf '%s\n' 'Docker daemon: unavailable to this user (check socket permissions)'
    fi
else
    printf '%s\n' 'Docker CLI unavailable'
fi

printf '\n%s\n' '-- Network listeners --'
ss -ltn 2>/dev/null | head -30 || true

printf '\n%s\n' '-- Qwen cache presence --'
model_volume="${VLLM_MODEL_VOLUME:-localrecall-qwen38-cache}"
if docker_cmd volume inspect "$model_volume" >/dev/null 2>&1; then
    printf 'Docker-managed model cache volume exists: %s\n' "$model_volume"
else
    printf 'Docker-managed model cache volume not created yet: %s\n' "$model_volume"
fi

printf '\n%s\n' 'Headless camera note: the Spark is not expected to have a webcam. Browser frames come from the presenter laptop.'
