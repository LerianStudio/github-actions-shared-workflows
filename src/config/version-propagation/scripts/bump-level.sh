#!/usr/bin/env bash
# Compares two semver tags and prints the bump level: major | minor | patch | none.
# Usage: bump-level.sh v1.28.5 v1.28.6  -> patch
set -euo pipefail

prev="${1#v}"
next="${2#v}"

IFS='.' read -r pM pm pp <<<"$prev"
IFS='.' read -r nM nm np <<<"$next"

if [[ "$nM" -gt "$pM" ]]; then echo major
elif [[ "$nm" -gt "$pm" ]]; then echo minor
elif [[ "$np" -gt "$pp" ]]; then echo patch
else echo none
fi
