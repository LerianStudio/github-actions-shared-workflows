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
