#!/usr/bin/env bash
set -u

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
    if docker info >/dev/null 2>&1; then
        printf '%s\n' 'Docker daemon: accessible'
        docker info --format 'Server={{.ServerVersion}} Root={{.DockerRootDir}}'
        docker image ls
    else
        printf '%s\n' 'Docker daemon: unavailable to this user (check socket permissions)'
    fi
else
    printf '%s\n' 'Docker CLI unavailable'
fi

printf '\n%s\n' '-- Network listeners --'
ss -ltn 2>/dev/null | head -30 || true

printf '\n%s\n' '-- Qwen cache presence --'
hf_cache="${HF_HOME:-$HOME/.cache/huggingface}/hub"
if [[ -d "$hf_cache" ]]; then
    find "$hf_cache" -maxdepth 3 -type d -name '*Qwen3.8-27B-NVFP4*' -print 2>/dev/null || true
else
    printf 'Hugging Face hub cache not found: %s\n' "$hf_cache"
fi

printf '\n%s\n' 'Headless camera note: the Spark is not expected to have a webcam. Browser frames come from the presenter laptop.'
