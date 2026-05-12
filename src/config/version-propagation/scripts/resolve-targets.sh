#!/usr/bin/env bash
# Reads the repository-keyed propagation matrix and emits one NDJSON line per
# enabled target:
#   {"repo":"...","target_branch":"...","workflow_files":[...],"auto_merge":{...}}
# An optional CSV filter (first arg) keeps only the listed repos.
#
# Usage: resolve-targets.sh [csv-filter]
# Required env: CONFIG_PATH (path to config/version-propagation.yml)
set -euo pipefail

config="${CONFIG_PATH:-config/version-propagation.yml}"
filter="${1:-}"

if [[ ! -f "$config" ]]; then
  echo "config not found: $config" >&2
  exit 1
fi

# Schema version gate: refuse anything other than v1 to surface intentional
# schema bumps as a clear error instead of letting a v2 config drift through.
schema_version=$(yq -r '.version // 0' "$config")
if [[ "$schema_version" != "1" ]]; then
  echo "unsupported config schema version: '$schema_version' (expected: 1)" >&2
  exit 1
fi

# Repository keys must match `owner/name`. Catching this upfront gives a
# better error than the downstream `git clone` failure.
while IFS= read -r key; do
  [[ -z "$key" ]] && continue
  if [[ ! "$key" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    echo "invalid repository key: '$key' (expected: owner/name)" >&2
    exit 1
  fi
done < <(yq -r '.repositories | keys | .[]' "$config")

yq -o=json '
  .defaults as $d
  | .repositories
  | to_entries
  | map({
      "repo": .key,
      "enabled": (.value.enabled // $d.enabled),
      "target_branch": (.value.target_branch // $d.target_branch),
      "workflow_files": (.value.workflow_files // $d.workflow_files),
      "auto_merge": (.value.auto_merge_pr_fallback // $d.auto_merge_pr_fallback)
    })
  | map(select(.enabled == true))
  | map(del(.enabled))
  | .[]
' "$config" \
  | jq -c '.' \
  | while IFS= read -r line; do
      if [[ -z "$filter" ]]; then
        echo "$line"
      else
        repo=$(jq -r '.repo' <<<"$line")
        if grep -q -F -x "$repo" <<<"$(tr ',' '\n' <<<"$filter" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"; then
          echo "$line"
        fi
      fi
    done
