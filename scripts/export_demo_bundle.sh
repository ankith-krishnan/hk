#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
commit="$(git rev-parse HEAD)"
short="${commit:0:12}"
output="${1:-data/exports/localrecall-demo-${short}.tar.gz}"
output_path="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).expanduser().resolve())' "$output")"
output_dir="$(dirname "$output_path")"
mkdir -p "$output_dir"
stage="$(mktemp -d)"
list_file="$(mktemp)"
trap 'rm -rf "$stage"; rm -f "$list_file"' EXIT

cat >"$stage/BUNDLE_INFO.txt" <<EOF
LocalRecall demo bundle
Git commit: $commit
Created UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Working tree changes: $(if [[ -n "$(git status --porcelain)" ]]; then echo present; else echo none; fi)
Backup video path reference: data/fixtures/recorded_trials/backup_video.mp4 (include separately if available; large videos are excluded)
Model checkpoint and virtual environments are intentionally excluded.
EOF

git ls-files --cached --others --exclude-standard |
    while IFS= read -r path; do
        [[ -f "$path" ]] || continue
        case "$path" in
            app/*|scripts/*|tests/*|*.md|*.toml|*.sh|*.env.example|Makefile|.gitignore|data/fixtures/*)
                ;;
            *) continue ;;
        esac
        case "$path" in
            .env|.venv/*|venv/*|*/__pycache__/*|data/objects/*|data/events/*|data/tmp/*|data/evaluation/generated/*|data/exports/*|*/.git/*)
                continue
                ;;
        esac
        size="$(stat -c %s "$path")"
        (( size <= 52428800 )) || continue
        printf '%s\n' "$path"
    done | sort -u >"$list_file"

if [[ -d data/evaluation/results ]]; then
    find data/evaluation/results -maxdepth 1 -type f \( -name '*.json' -o -name '*.md' \) -size -50M -print |
        sed "s#^$root/##" >>"$list_file"
fi
if [[ -d screenshots ]]; then
    find screenshots -type f -size -50M -print |
        sed "s#^$root/##" >>"$list_file"
fi
sort -u -o "$list_file" "$list_file"

tar -czf "$output_path" -C "$root" -T "$list_file" -C "$stage" BUNDLE_INFO.txt
printf 'Created demo bundle: %s\n' "$output_path"
printf 'Git commit: %s\n' "$commit"
printf 'Included paths: %s\n' "$(wc -l <"$list_file" | tr -d ' ')"
