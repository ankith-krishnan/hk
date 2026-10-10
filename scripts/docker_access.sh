#!/usr/bin/env bash

# Run Docker as the current user when possible, otherwise use passwordless sudo.
docker_cmd() {
    if command docker info >/dev/null 2>&1; then
        command docker "$@"
    elif command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
        sudo -n docker "$@"
    else
        printf 'Docker daemon is unavailable to this account (tried docker and sudo -n docker).\n' >&2
        return 1
    fi
}
