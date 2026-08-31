#!/usr/bin/env bash
# Reads `config/tier-promotion.yml`, validates it, and emits the flow as JSON:
#   {"tiers":[{"branch":"tier-0","environment":"tier-0","concurrency_group":"...","auto_merge_pr_fallback":false,"description":"..."}],
#    "source_branch":"main","stable_tag_pattern":"..."}
#
# Also enforces agreement with the STATIC job chain that implements the flow.
# GitHub Actions cannot build a job graph from data: the `needs:` chain and the
# `environment:` of each promotion job are written literally in
# `.github/workflows/tier-promotion.yml`. The environment names in particular
# are deliberately NOT interpolated from this config — an approval gate that
# resolves through an expression could be pointed at an ungated environment by
# editing a config file, while a literal `environment: tier-1` in the workflow
# is auditable by reading it. The cost of that choice is drift, so this script
# fails the run when config and workflow disagree.
#
# Usage: resolve-flow.sh
# Required env:
#   CONFIG_PATH   path to config/tier-promotion.yml
#   EXPECTED_FLOW ordered CSV of `branch:environment` implemented by the
#                 workflow, e.g. "tier-0:tier-0,tier-1:tier-1,tier-2:tier-2"
set -euo pipefail

config="${CONFIG_PATH:-config/tier-promotion.yml}"
: "${EXPECTED_FLOW:?EXPECTED_FLOW is required}"

if [[ ! -f "$config" ]]; then
  echo "::error::config not found: $config"
  exit 1
fi

# Schema version gate: refuse anything other than v1 so an intentional schema
# bump surfaces as a clear error instead of silently changing behaviour.
schema_version=$(yq -r '.version // 0' "$config")
if [[ "$schema_version" != "1" ]]; then
  echo "::error::unsupported schema version '$schema_version' in $config (expected 1)"
  exit 1
fi

tiers_kind=$(yq -r '.tiers | type' "$config")
if [[ "$tiers_kind" != "!!seq" ]]; then
  echo "::error::.tiers must be a sequence (ordered list), got '$tiers_kind'"
  exit 1
fi

tiers_count=$(yq -r '.tiers | length' "$config")
if [[ "$tiers_count" -lt 1 ]]; then
  echo "::error::.tiers is empty — nothing to promote"
  exit 1
fi

# Every tier needs a branch and a concurrency group. `environment` may be an
# empty string (no environment, therefore no deployment record) but the key
# must be present so the omission is explicit rather than accidental.
for i in $(seq 0 $((tiers_count - 1))); do
  branch=$(yq -r ".tiers[$i].branch // \"\"" "$config")
  group=$(yq -r ".tiers[$i].concurrency_group // \"\"" "$config")
  has_env=$(yq -r ".tiers[$i] | has(\"environment\")" "$config")

  if [[ -z "$branch" ]]; then
    echo "::error::.tiers[$i] is missing required key 'branch'"
    exit 1
  fi
  if [[ ! "$branch" =~ ^tier-[0-9]+$ ]]; then
    # The `tier-rule` ruleset only covers `refs/heads/tier-*`. A branch outside
    # that pattern would be promoted without deletion or force-push protection.
    echo "::error::.tiers[$i].branch '$branch' must match ^tier-[0-9]+$ to be covered by the tier-rule ruleset"
    exit 1
  fi
  if [[ -z "$group" ]]; then
    echo "::error::.tiers[$i] ($branch) is missing required key 'concurrency_group'"
    exit 1
  fi
  if [[ "$has_env" != "true" ]]; then
    echo "::error::.tiers[$i] ($branch) must declare 'environment' (use \"\" to opt out explicitly)"
    exit 1
  fi
done

# Distinct concurrency groups are load-bearing, not cosmetic: sharing a group
# parks an early-tier promotion behind an approval pending on a later tier,
# which inverts the purpose of the early tier.
dupes=$(yq -r '.tiers[].concurrency_group' "$config" | sort | uniq -d)
if [[ -n "$dupes" ]]; then
  echo "::error::concurrency_group must be unique per tier — repeated: $(tr '\n' ' ' <<<"$dupes")"
  exit 1
fi

actual_flow=$(yq -r '[.tiers[] | .branch + ":" + (.environment // "")] | join(",")' "$config")
if [[ "$actual_flow" != "$EXPECTED_FLOW" ]]; then
  echo "::error::config/tier-promotion.yml no longer matches the job chain in .github/workflows/tier-promotion.yml"
  echo "::error::config:   $actual_flow"
  echo "::error::workflow: $EXPECTED_FLOW"
  echo "::error::Update the workflow's job chain (needs: and environment:) to match, then update EXPECTED_FLOW."
  exit 1
fi

# yq converts the document to JSON; the shaping happens in jq. mikefarah's yq
# has no `if/then/else`, and the boolean defaults below genuinely need one:
# `//` treats an explicit `false` as absent, so a tier that deliberately sets
# `auto_merge_pr_fallback: false` would silently inherit a `true` default.
# Booleans therefore go through `has()`.
yq -o=json -I=0 '{"defaults": (.defaults // {}), "tiers": .tiers}' "$config" \
  | jq -c '
    .defaults as $d |
    {
      source_branch: ($d.source_branch // "main"),
      stable_tag_pattern: ($d.stable_tag_pattern // "^v[0-9]+\\.[0-9]+\\.[0-9]+$"),
      tiers: [
        .tiers[] | {
          branch: .branch,
          environment: (.environment // ""),
          concurrency_group: .concurrency_group,
          description: (.description // ""),
          auto_merge_pr_fallback: (
            if has("auto_merge_pr_fallback") then .auto_merge_pr_fallback
            elif ($d | has("auto_merge_pr_fallback")) then $d.auto_merge_pr_fallback
            else false end
          )
        }
      ]
    }'
