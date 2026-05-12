#!/usr/bin/env bash
# Compares two semver tags and prints the bump level: major | minor | patch | none.
# Usage: bump-level.sh v1.28.5 v1.28.6  -> patch
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: bump-level.sh <prev-tag> <next-tag>" >&2
  exit 1
fi

prev="${1#v}"
next="${2#v}"

semver_re='^[0-9]+\.[0-9]+\.[0-9]+$'
if [[ ! "$prev" =~ $semver_re ]]; then
  echo "invalid semver: '$1'" >&2
  exit 1
fi
if [[ ! "$next" =~ $semver_re ]]; then
  echo "invalid semver: '$2'" >&2
  exit 1
fi

IFS='.' read -r pM pm pp <<<"$prev"
IFS='.' read -r nM nm np <<<"$next"

if [[ "$nM" -gt "$pM" ]]; then echo major
elif [[ "$nm" -gt "$pm" ]]; then echo minor
elif [[ "$np" -gt "$pp" ]]; then echo patch
else echo none
fi
