#!/usr/bin/env bash

# Decides whether a pull request falls inside a gate's scope, and says why.
#
# Scope is a base -> head mapping rather than two independent dimensions,
# because "where is this landing" is usually the question a gate is really
# asking. A pull request is in scope when its base branch appears in the rules
# and its head branch matches one of that base's globs.
#
# Reads the live pull request through `gh` rather than the event payload, which
# is frozen at dispatch: a run started before a retarget would otherwise decide
# against a base branch that no longer applies.
#
# Order of decision, and it matters:
#
#   1. ignored authors  a veto, before anything else
#   2. skip labels      an explicit opt-out
#   3. base -> head     the rules
#   4. force labels     an explicit opt-in for what the rules missed
#
# The vetoes come first on purpose. Expressed as extra scope dimensions they
# would be OR'd with the positive ones and lose to any match.

set -euo pipefail

GH_TOKEN=${GH_TOKEN:-}
REPO=${REPO:-}
PR_NUMBER=${PR_NUMBER:-}
SCOPE_RULES=${SCOPE_RULES:-}
ADDITIONAL_SCOPE_RULES=${ADDITIONAL_SCOPE_RULES:-}
FORCE_LABELS=${FORCE_LABELS:-}
SKIP_LABELS=${SKIP_LABELS:-}
IGNORE_AUTHORS=${IGNORE_AUTHORS:-}
VERBOSE=${VERBOSE:-false}

export GH_TOKEN

if [[ -z "${REPO}" ]]; then
  printf 'PR Gate Scope: REPO is required.\n' >&2
  exit 1
fi

if [[ -z "${PR_NUMBER}" || "${PR_NUMBER}" == 0 ]]; then
  printf 'PR Gate Scope: PR_NUMBER is required — pass the number explicitly or call from an event that carries one.\n' >&2
  exit 1
fi

for binary in gh jq; do
  if ! command -v "${binary}" >/dev/null 2>&1; then
    printf 'PR Gate Scope: %s is not available.\n' "${binary}" >&2
    exit 1
  fi
done

read -r base head head_sha author < <(
  gh pr view "${PR_NUMBER}" --repo "${REPO}" \
    --json baseRefName,headRefName,headRefOid,author \
    --jq '"\(.baseRefName) \(.headRefName) \(.headRefOid) \(.author.login)"'
)

if [[ -z "${base}" || -z "${head}" ]]; then
  printf 'PR Gate Scope: could not read PR #%s in %s.\n' "${PR_NUMBER}" "${REPO}" >&2
  exit 1
fi

labels=$(gh pr view "${PR_NUMBER}" --repo "${REPO}" --json labels --jq '.labels[].name')

# Bot logins have three spellings and all of them must match. REST returns
# `dependabot[bot]`, GraphQL returns `dependabot`, and `gh pr view --json author`
# — the call above — returns `app/dependabot`, because the CLI prefixes bot
# logins with `app/`. Strip both affixes from both sides so a caller can write
# whichever spelling it last saw.
# `tr` rather than `${var,,}`: the parameter expansion is bash 4+, and macOS
# ships bash 3.2 — test.sh has to run on a contributor's laptop, not only on the
# runner.
lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

normalise_login() {
  local login
  login=$(lower "$1")
  login="${login#app/}"
  printf '%s' "${login%\[bot\]}"
}

has_label() {
  local wanted name
  wanted=$(lower "$1")
  while IFS= read -r name; do
    [[ -z "${name}" ]] && continue
    [[ "$(lower "${name}")" == "${wanted}" ]] && return 0
  done <<< "${labels}"
  return 1
}

matches_any_label() {
  local list=$1 entry
  while IFS= read -r entry; do
    [[ -z "${entry}" ]] && continue
    if has_label "${entry}"; then
      printf '%s' "${entry}"
      return 0
    fi
  done < <(tr ',' '\n' <<< "${list}" | xargs -n1 2>/dev/null)
  return 1
}

emit() {
  printf 'in-scope=%s\n' "$1"
  printf 'reason=%s\n' "$2"
  printf 'pr-number=%s\n' "${PR_NUMBER}"
  printf 'base-ref=%s\n' "${base}"
  printf 'head-ref=%s\n' "${head}"
  printf 'head-sha=%s\n' "${head_sha}"
  printf 'author=%s\n' "${author}"
}

if [[ "${VERBOSE}" == true ]]; then
  {
    printf '  pull request      : #%s\n' "${PR_NUMBER}"
    printf '  head -> base      : %s -> %s\n' "${head}" "${base}"
    printf '  head commit       : %s\n' "${head_sha}"
    printf '  author            : %s\n' "${author}"
    printf '  labels            : [%s]\n' "$(tr '\n' ',' <<< "${labels}" | sed 's/,$//')"
    printf '  scope rules       : %s\n' "${SCOPE_RULES}"
    printf '  additional rules  : [%s]\n' "${ADDITIONAL_SCOPE_RULES}"
    printf '  force labels      : [%s]\n' "${FORCE_LABELS}"
    printf '  skip labels       : [%s]\n' "${SKIP_LABELS}"
    printf '  ignored authors   : [%s]\n' "${IGNORE_AUTHORS}"
  } >&2
fi

author_key=$(normalise_login "${author}")
while IFS= read -r entry; do
  [[ -z "${entry}" ]] && continue
  if [[ "${author_key}" == "$(normalise_login "${entry}")" ]]; then
    emit false "ignored author '${author}'"
    exit 0
  fi
done < <(tr ',' '\n' <<< "${IGNORE_AUTHORS}" | xargs -n1 2>/dev/null)

if [[ -n "${SKIP_LABELS}" ]] && skip_hit=$(matches_any_label "${SKIP_LABELS}"); then
  emit false "skip label '${skip_hit}'"
  exit 0
fi

# Both objects are validated before the merge so a malformed rule set fails
# closed here, rather than silently producing an empty rule set that gates
# nothing while still reporting success.
validate_rules() {
  jq -e 'type == "object" and (to_entries | all(.value | type == "string"))' \
    >/dev/null 2>&1 <<< "$1"
}

additional=${ADDITIONAL_SCOPE_RULES:-}
[[ -z "${additional}" ]] && additional='{}'

if ! validate_rules "${SCOPE_RULES}"; then
  printf 'PR Gate Scope: scope-rules must be a JSON object of string values; got: %s\n' \
    "${SCOPE_RULES}" >&2
  exit 1
fi

if ! validate_rules "${additional}"; then
  printf 'PR Gate Scope: additional-scope-rules must be a JSON object of string values; got: %s\n' \
    "${ADDITIONAL_SCOPE_RULES}" >&2
  exit 1
fi

# `*` is a shallow merge: a base present in both takes the additional value, a
# base present only in the additional set is added.
rules=$(jq -cn --argjson base "${SCOPE_RULES}" --argjson extra "${additional}" '$base * $extra')
patterns=$(jq -r --arg base "${base}" '.[$base] // ""' <<< "${rules}")

matched=''
while IFS= read -r entry; do
  [[ -z "${entry}" ]] && continue
  # shellcheck disable=SC2254  # the pattern is a glob on purpose
  case "${head}" in
    ${entry}) matched="rule ${base} <- '${entry}'"; break ;;
  esac
done < <(tr '|' '\n' <<< "${patterns}" | xargs -n1 2>/dev/null)

if [[ -z "${matched}" && -n "${FORCE_LABELS}" ]] && force_hit=$(matches_any_label "${FORCE_LABELS}"); then
  matched="force label '${force_hit}'"
fi

if [[ -z "${matched}" ]]; then
  emit false "no rule matches ${head} -> ${base}"
  exit 0
fi

emit true "${matched}"
