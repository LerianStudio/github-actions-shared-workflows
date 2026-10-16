#!/usr/bin/env bash

# Lists the commits in a pull request that carry a breaking change, and
# fingerprints the set.
#
# Two consumers need this and for different reasons:
#
#   the comment, to show the author their own subjects rather than a made-up
#   example
#
#   the gate, to tell "the approved breaking change is still the same one" from
#   "something new arrived". Without that, every push expires an approval given
#   minutes earlier for identical content, and a reviewer is asked the same
#   question again — which is how a gate becomes a formality.
#
# Read through the API rather than Git, because the jobs that need it have no
# checkout. The canonical detector remains `breaking-change-guard`, which runs
# over the real commit range; this must agree with it, and the patterns below
# are kept identical to the ones pinned there.

set -euo pipefail

GH_TOKEN=${GH_TOKEN:-}
REPO=${REPO:-}
PR_NUMBER=${PR_NUMBER:-}

export GH_TOKEN

if [[ -z "${REPO}" || -z "${PR_NUMBER}" ]]; then
  printf 'Breaking Change Commits: REPO and PR_NUMBER are required.\n' >&2
  exit 1
fi

for binary in gh jq; do
  if ! command -v "${binary}" >/dev/null 2>&1; then
    printf 'Breaking Change Commits: %s is not available.\n' "${binary}" >&2
    exit 1
  fi
done

if ! commits=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/commits" --paginate \
                 --jq '.[] | [.sha, .commit.message] | @base64' 2>/dev/null); then
  printf 'Breaking Change Commits: could not read the commits of PR #%s in %s.\n' \
    "${PR_NUMBER}" "${REPO}" >&2
  exit 1
fi

shas=''
subjects=''
count=0

# `!` after the type, or a `BREAKING CHANGE` footer. Same two forms the
# detector accepts, and deliberately no others: `BREAKING-CHANGE` and `-`
# bullets are not breaking to the release parser either.
is_breaking() {
  local message=$1 subject line

  subject=$(head -n1 <<< "${message}")
  if [[ "${subject}" =~ ^[A-Za-z0-9_]*(\([^\)]*\))?!:\  ]]; then
    return 0
  fi

  while IFS= read -r line; do
    line=${line%$'\r'}
    if [[ "${line}" =~ ^[[:space:]\|\*]*[Bb][Rr][Ee][Aa][Kk][Ii][Nn][Gg][[:space:]][Cc][Hh][Aa][Nn][Gg][Ee][Ss]?([:[:space:]]) ]]; then
      return 0
    fi
  done <<< "${message}"

  return 1
}

while IFS= read -r encoded; do
  [[ -z "${encoded}" ]] && continue

  entry=$(base64 --decode <<< "${encoded}" 2>/dev/null || true)
  [[ -z "${entry}" ]] && continue

  sha=$(jq -r '.[0]' <<< "${entry}" 2>/dev/null || true)
  message=$(jq -r '.[1]' <<< "${entry}" 2>/dev/null || true)
  [[ -z "${sha}" ]] && continue

  if is_breaking "${message}"; then
    shas="${shas:+${shas},}${sha}"
    subjects="${subjects}$(head -n1 <<< "${message}")"$'\n'
    count=$((count + 1))
  fi
done <<< "${commits}"

# The fingerprint answers one question: is this the same set that was approved?
# Built from the SHAs, so rewording or reordering produces a different one —
# the commit is not the same commit, and the approval was for the old text.
fingerprint=''
if [[ -n "${shas}" ]]; then
  fingerprint=$(printf '%s' "${shas}" | shasum -a 256 2>/dev/null | cut -c1-16) \
    || fingerprint=$(printf '%s' "${shas}" | sha256sum | cut -c1-16)
fi

printf 'count=%s\n' "${count}"
printf 'shas=%s\n' "${shas}"
printf 'fingerprint=%s\n' "${fingerprint}"
{
  printf 'subjects<<BREAKING_SUBJECTS_EOF\n'
  printf '%s' "${subjects}"
  printf 'BREAKING_SUBJECTS_EOF\n'
}
