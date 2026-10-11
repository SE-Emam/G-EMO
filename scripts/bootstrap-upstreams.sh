#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="$ROOT/research/repos"

ensure_pinned_checkout() {
  local name="$1"
  local url="$2"
  local path="$3"
  local commit="$4"

  if [[ ! -d "$path/.git" ]]; then
    mkdir -p "$(dirname "$path")"
    echo "Cloning $name into $path"
    git clone "$url" "$path"
    git -C "$path" checkout --detach "$commit"
    return
  fi

  local existing_url
  existing_url="$(git -C "$path" remote get-url origin)"
  if [[ "$existing_url" != "$url" ]]; then
    echo "BLOCKED: $path has unexpected origin: $existing_url" >&2
    echo "Expected: $url" >&2
    exit 2
  fi

  local current_commit
  current_commit="$(git -C "$path" rev-parse HEAD)"
  if [[ "$current_commit" != "$commit" ]]; then
    echo "BLOCKED: $path is at $current_commit, expected pinned commit $commit." >&2
    echo "Existing checkout was not changed. Review it manually before switching revisions." >&2
    exit 2
  fi

  if [[ -n "$(git -C "$path" status --porcelain)" ]]; then
    echo "BLOCKED: $path has uncommitted changes; leaving it untouched." >&2
    exit 2
  fi

  echo "PASS: $name is already at pinned commit $commit"
}

ensure_pinned_checkout \
  "PicoClaw" \
  "https://github.com/sipeed/picoclaw.git" \
  "$BASE/picoclaw" \
  "bbf6893ca7afad27f1d00a0f5a45982a549c6ed6"

ensure_pinned_checkout \
  "PicoClaw FUI" \
  "https://github.com/sipeed/picoclaw_fui.git" \
  "$BASE/picoclaw-fui" \
  "d689c94c1b67f625f70ec4111a9aa3f01be9cbb3"

echo "Pinned upstream baselines are ready. This script does not fetch or recreate the missing EMO adapter/FUI integration branches."
