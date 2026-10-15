#!/usr/bin/env bash

# Turns a repository's CODEOWNERS into the reviewer list an Environment gate
# needs: `team:<slug>,user:<login>`.
#
# The people who own the code are the people who should answer a gate about it,
# and CODEOWNERS is where a repository already states that. Deriving from it
# means a gate shipped to a hundred repositories asks each one's own owners,
# with nothing to configure.
#
# Read through the API rather than the working tree, because the job that needs
# this has no checkout — and, more importantly, it must read the BASE ref. A
# CODEOWNERS taken from the pull request head would let the author edit who is
# allowed to approve their own change.
#
# GitHub resolves CODEOWNERS from three locations, in this order, and so does
# this: .github/, the root, then docs/.

set -euo pipefail

GH_TOKEN=${GH_TOKEN:-}
REPO=${REPO:-}
REF=${REF:-}
PATTERN=${PATTERN:-}
MAX_REVIEWERS=${MAX_REVIEWERS:-6}

export GH_TOKEN

if [[ -z "${REPO}" ]]; then
  printf 'CODEOWNERS Reviewers: REPO is required.\n' >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  printf 'CODEOWNERS Reviewers: gh is not available.\n' >&2
  exit 1
fi

fetch_codeowners() {
  local path=$1
  local query="repos/${REPO}/contents/${path}"
  [[ -n "${REF}" ]] && query="${query}?ref=${REF}"
  gh api "${query}" -H 'Accept: application/vnd.github.raw' 2>/dev/null
}

content=''
source_path=''
for candidate in .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS; do
  if content=$(fetch_codeowners "${candidate}") && [[ -n "${content}" ]]; then
    source_path=${candidate}
    break
  fi
  content=''
done

if [[ -z "${content}" ]]; then
  printf 'CODEOWNERS Reviewers: no CODEOWNERS found in %s (looked in .github/, the root and docs/).\n' \
    "${REPO}" >&2
  printf 'found=false\n'
  printf 'reviewers=\n'
  printf 'source=\n'
  exit 0
fi

# The last matching rule wins in CODEOWNERS, so the owners are collected by
# overwriting rather than by stopping at the first hit.
owners=()
matched_rule=''

while IFS= read -r line; do
  line=${line%$'\r'}
  line=${line%%#*}

  # Section headers from the Enterprise syntax — `[Name]` or `^[Name]` — carry
  # no owners of their own and must not be read as a pattern.
  case "${line}" in
    '' | '['* | '^['* ) continue ;;
  esac

  # `read -ra`, not `set -- ${line}`: unquoted word splitting also globs, and
  # the most common CODEOWNERS pattern is `*` — which would expand to the
  # runner's working directory and match nothing ever again.
  read -ra fields <<< "${line}"
  [[ ${#fields[@]} -lt 2 ]] && continue

  rule_pattern=${fields[0]}
  [[ "${rule_pattern}" != "${PATTERN:-*}" ]] && continue

  owners=("${fields[@]:1}")
  matched_rule=${rule_pattern}
done <<< "${content}"

if [[ ${#owners[@]} -eq 0 ]]; then
  printf 'CODEOWNERS Reviewers: %s has no rule for %s, so no owners could be derived.\n' \
    "${source_path}" "${PATTERN:-*}" >&2
  printf 'found=false\n'
  printf 'reviewers=\n'
  printf 'source=%s\n' "${source_path}"
  exit 0
fi

reviewers=''
count=0
dropped=''

for owner in "${owners[@]}"; do
  case "${owner}" in
    @*/*)
      entry="team:${owner#*/}"
      ;;
    @*)
      entry="user:${owner#@}"
      ;;
    *)
      # An email address identifies a person GitHub will not resolve to a
      # reviewer here. Dropped out loud rather than silently.
      dropped="${dropped:+$dropped, }${owner}"
      continue
      ;;
  esac

  # An Environment takes at most six reviewers. Truncating quietly would make a
  # gate narrower than the repository declared, so say which ones were cut.
  if [[ ${count} -ge ${MAX_REVIEWERS} ]]; then
    dropped="${dropped:+$dropped, }${owner}"
    continue
  fi

  case ",${reviewers}," in
    *",${entry},"* ) continue ;;
  esac

  reviewers="${reviewers:+$reviewers,}${entry}"
  count=$((count + 1))
done

if [[ -n "${dropped}" ]]; then
  printf 'CODEOWNERS Reviewers: not used as reviewers: %s (emails cannot be resolved; at most %s reviewers are allowed).\n' \
    "${dropped}" "${MAX_REVIEWERS}" >&2
fi

if [[ -z "${reviewers}" ]]; then
  printf 'CODEOWNERS Reviewers: %s matched rule %s but none of its owners can be a reviewer.\n' \
    "${source_path}" "${matched_rule}" >&2
  printf 'found=false\n'
  printf 'reviewers=\n'
  printf 'source=%s\n' "${source_path}"
  exit 0
fi

printf 'found=true\n'
printf 'reviewers=%s\n' "${reviewers}"
printf 'source=%s\n' "${source_path}"
