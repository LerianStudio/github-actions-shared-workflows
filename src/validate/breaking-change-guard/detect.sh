#!/usr/bin/env bash

set -euo pipefail

BASE_REF=${BASE_REF:-}
PR_BODY=${PR_BODY:-}
ACK=${ACK:-}
AWK_BIN=${AWK:-awk}

if [[ -z "${BASE_REF}" ]]; then
  printf 'Breaking Change Guard: BASE_REF is required.\n' >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  printf 'Breaking Change Guard: git is not available.\n' >&2
  exit 1
fi

if ! command -v "${AWK_BIN}" >/dev/null 2>&1; then
  printf 'Breaking Change Guard: awk implementation %q is not available.\n' "${AWK_BIN}" >&2
  exit 1
fi

if [[ $(git rev-parse --is-shallow-repository 2>/dev/null) == true ]]; then
  printf 'Breaking Change Guard: shallow repository detected; fetch full history before running.\n' >&2
  exit 1
fi

if ! base_commit=$(git rev-parse --verify --quiet \
  "refs/remotes/origin/${BASE_REF}^{commit}"); then
  printf 'Breaking Change Guard: base ref origin/%s is missing or invalid.\n' \
    "${BASE_REF}" >&2
  exit 1
fi

if ! head_commit=$(git rev-parse --verify --quiet 'HEAD^{commit}'); then
  printf 'Breaking Change Guard: HEAD is missing or invalid.\n' >&2
  exit 1
fi

message_file=$(mktemp "${TMPDIR:-/tmp}/breaking-change-guard.XXXXXX")
cleanup() {
  rm -f "${message_file}"
}
trap cleanup EXIT INT TERM

if ! git log --format='%B%x1e' \
  "${base_commit}..${head_commit}" >"${message_file}" 2>/dev/null; then
  printf 'Breaking Change Guard: git log failed for origin/%s..HEAD.\n' \
    "${BASE_REF}" >&2
  exit 1
fi

# The awk program is intentionally a literal string.
# shellcheck disable=SC2016
has_breaking_changes=$("${AWK_BIN}" '
  BEGIN {
    RS = sprintf("%c", 30)
    found = 0
  }
  {
    message = $0
    while (substr(message, 1, 1) == "\n" || substr(message, 1, 1) == "\r") {
      message = substr(message, 2)
    }

    line_count = split(message, lines, "\n")
    subject = tolower(lines[1])
    if (subject ~ /^[a-z0-9_]*(\(.*\))?!: .*$/) {
      found = 1
    }

    for (line_number = 1; line_number <= line_count; line_number++) {
      line = tolower(lines[line_number])
      sub(/\r$/, "", line)
      if (line ~ /^[[:space:]|*]*breaking changes?(:|[[:space:]])+/) {
        found = 1
      }
    }
  }
  END {
    print found ? "true" : "false"
  }
' "${message_file}")

approved=false
if [[ -n "${ACK}" && "${PR_BODY}" == *"${ACK}"* ]]; then
  approved=true
fi

printf 'has-breaking-changes=%s\n' "${has_breaking_changes}"
printf 'approved=%s\n' "${approved}"

if [[ "${has_breaking_changes}" == true ]]; then
  printf 'Breaking Change Guard: breaking-change commit(s) detected; acknowledgement present: %s.\n' \
    "${approved}" >&2
fi
