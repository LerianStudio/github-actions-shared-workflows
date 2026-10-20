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
# Optional. Resolves the set as it stood at a given revision instead of at the
# pull request's current head — which is what lets the gate ask the question it
# actually needs answered: what did that approval approve? Reading the
# fingerprint out of a comment answers a different one, and a comment is
# writable by anybody who can read the repository.
BASE_REF=${BASE_REF:-}
AT_SHA=${AT_SHA:-}

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

if [[ -n "${AT_SHA}" ]]; then
  if [[ -z "${BASE_REF}" ]]; then
    printf 'Breaking Change Commits: BASE_REF is required with AT_SHA.\n' >&2
    exit 1
  fi

  # `compare` answers for a revision that is no longer the head. The pull
  # request's own commits endpoint cannot: it always reports the current state.
  if ! comparison=$(gh api "repos/${REPO}/compare/${BASE_REF}...${AT_SHA}" 2>/dev/null); then
    printf 'Breaking Change Commits: could not compare %s...%s in %s.\n' \
      "${BASE_REF}" "${AT_SHA}" "${REPO}" >&2
    exit 1
  fi

  # Same cap, same refusal. `compare` returns at most 250 commits and declares
  # the real total separately, so a truncated answer is detectable — and
  # answering from one would be worse here than anywhere else, since this
  # decides whether an approval is reused.
  declared_total=$(jq -r '.total_commits // 0' <<< "${comparison}")
  returned_total=$(jq -r '.commits | length' <<< "${comparison}")
  if [[ "${declared_total}" -ne "${returned_total}" ]]; then
    printf 'Breaking Change Commits: %s...%s has %s commits but the comparison returned %s.\n' \
      "${BASE_REF}" "${AT_SHA}" "${declared_total}" "${returned_total}" >&2
    exit 1
  fi

  commits=$(jq -r '.commits[] | [.sha, .commit.message] | @base64' <<< "${comparison}")
elif ! commits=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/commits" --paginate \
                 --jq '.[] | [.sha, .commit.message] | @base64' 2>/dev/null); then
  printf 'Breaking Change Commits: could not read the commits of PR #%s in %s.\n' \
    "${PR_NUMBER}" "${REPO}" >&2
  exit 1
fi

# The commits endpoint returns at most 250, pagination or not. GitHub documents
# this, and answering from a truncated list is worse than not answering: a break
# living past the cap reads as "no breaking change", and — with reuse — an
# approved break inside the window plus an omitted one outside it leaves the
# fingerprint unchanged, so an approval is honoured for a change it never
# covered.
#
# Refuse instead. A gate that cannot see the whole change says so.
#
# Only for the pull-request path: the comparison above does its own version of
# this check, against `total_commits`, because it has no pull request to ask.
returned=$(grep -c . <<< "${commits}" || true)
[[ -z "${commits}" ]] && returned=0

if [[ -n "${AT_SHA}" ]]; then
  declared="${returned}"
elif ! declared=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}" --jq '.commits' 2>/dev/null); then
  printf 'Breaking Change Commits: could not read the commit count of PR #%s in %s.\n' \
    "${PR_NUMBER}" "${REPO}" >&2
  exit 1
fi

if [[ "${returned}" -ne "${declared}" ]]; then
  printf 'Breaking Change Commits: PR #%s declares %s commits but the API returned %s.\n' \
    "${PR_NUMBER}" "${declared}" "${returned}" >&2
  printf 'The commits endpoint caps at 250, so this enumeration is incomplete and a verdict from it would be a guess.\n' >&2
  exit 1
fi

shas=''
subjects=''
count=0

# `!` after the type, or a `BREAKING CHANGE` footer. Same two forms the
# detector accepts, and deliberately no others: `BREAKING-CHANGE` and `-`
# bullets are not breaking to the release parser either.
# Transcribed from the detector's awk, which lowercases the line first and then
# applies:
#
#   subject  ^[a-z0-9_]*(\(.*\))?!: .*$
#   footer   ^[[:space:]|*]*breaking changes?(:|[[:space:]])+
#
# Held in variables because a bare `|` inside `[[ =~ ]]` is parsed as an
# operator, and because the two must be read side by side with the detector to
# stay honest. `\(.*\)` for the scope, not `\([^)]*\)`: a scope containing a
# closing paren matches there, so it has to match here.
BANG_SUBJECT_RE='^[a-z0-9_]*(\(.*\))?!: '
# `[[:space:]|*]` — inside a bracket expression a backslash is a literal
# backslash, so escaping `|` and `*` there would quietly widen the class to
# accept a leading `\`.
FOOTER_RE='^[[:space:]|*]*breaking changes?(:|[[:space:]])'

is_breaking() {
  local message=$1 subject line lowered

  subject=$(printf '%s' "${message}" | head -n1 | tr '[:upper:]' '[:lower:]')
  if [[ "${subject}" =~ ${BANG_SUBJECT_RE} ]]; then
    return 0
  fi

  while IFS= read -r line; do
    line=${line%$'\r'}
    lowered=$(printf '%s' "${line}" | tr '[:upper:]' '[:lower:]')
    if [[ "${lowered}" =~ ${FOOTER_RE} ]]; then
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
# The subjects are commit-controlled text going into GITHUB_OUTPUT. With a
# fixed delimiter, a commit whose subject IS that delimiter closes the block
# early and every line after it becomes a new output assignment — including
# `fingerprint=`, which is what decides whether this breaking change was
# already approved. That is a gate bypass written by whoever opens the pull
# request, so the delimiter is random per run and verified not to appear.
delimiter="BREAKING_SUBJECTS_$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
while grep -Fqx -- "${delimiter}" <<< "${subjects}"; do
  delimiter="BREAKING_SUBJECTS_$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
done

{
  printf 'subjects<<%s\n' "${delimiter}"
  printf '%s' "${subjects}"
  printf '%s\n' "${delimiter}"
}
