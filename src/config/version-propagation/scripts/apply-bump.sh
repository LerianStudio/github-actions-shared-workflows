#!/usr/bin/env bash
# Rewrites @vX.Y.Z pins of LerianStudio/github-actions-shared-workflows inside
# the workflow files matching the given globs. Run from the root of a checked-out
# target repository.
#
# Usage: apply-bump.sh <new-tag> <glob1> [glob2 ...]
# Exit codes: 0 ok (files changed), 10 ok (no changes needed).
set -euo pipefail

new_tag="$1"; shift
changed=0

if [[ ! "$new_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "refusing to apply non-stable tag: $new_tag" >&2
  exit 1
fi

shopt -s nullglob globstar

for glob in "$@"; do
  for f in .github/workflows/$glob; do
    [[ -f "$f" ]] || continue
    if grep -qE 'LerianStudio/github-actions-shared-workflows[^@]*@v[0-9]+\.[0-9]+\.[0-9]+' "$f"; then
      before=$(sha1sum "$f" | awk '{print $1}')
      sed -E -i \
        "s|(LerianStudio/github-actions-shared-workflows[^@[:space:]]*@)v[0-9]+\\.[0-9]+\\.[0-9]+|\\1${new_tag}|g" \
        "$f"
      after=$(sha1sum "$f" | awk '{print $1}')
      if [[ "$before" != "$after" ]]; then
        echo "rewrote: $f"
        changed=1
      fi
    fi
  done
done

if [[ "$changed" -eq 0 ]]; then
  exit 10
fi
