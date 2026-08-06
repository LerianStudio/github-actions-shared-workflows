#!/usr/bin/env bash

set -euo pipefail

BASE_REF=${BASE_REF:-}
PR_BODY=${PR_BODY:-}
ACK=${ACK:-}
ACKNOWLEDGEMENT_MATCH_MODE=${ACKNOWLEDGEMENT_MATCH_MODE:-}
AWK_BIN=${AWK:-awk}

case "${ACKNOWLEDGEMENT_MATCH_MODE}" in
  contains | exact-visible-line) ;;
  *)
    printf 'Breaking Change Guard: ACKNOWLEDGEMENT_MATCH_MODE must be one of: contains, exact-visible-line.\n' >&2
    exit 1
    ;;
esac

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
if [[ -n "${ACK}" ]]; then
  case "${ACKNOWLEDGEMENT_MATCH_MODE}" in
    contains)
      if [[ "${PR_BODY}" == *"${ACK}"* ]]; then
        approved=true
      fi
      ;;
    exact-visible-line)
      # The awk program is intentionally a literal string.
      # shellcheck disable=SC2016
      approved=$(printf '%s' "${PR_BODY}" | "${AWK_BIN}" '
        function leading_fence_length(value, character, candidate, count) {
          candidate = value
          sub(/^[[:space:]]*/, "", candidate)
          count = 0
          while (substr(candidate, count + 1, 1) == character) {
            count++
          }
          return count
        }

        BEGIN {
          acknowledgement = ENVIRON["ACK"]
          in_comment = 0
          in_fence = 0
          found = 0
        }
        {
          line = $0
          sub(/\r$/, "", line)

          if (in_fence) {
            closing_length = leading_fence_length(line, fence_character)
            closing_line = line
            sub(/^[[:space:]]*/, "", closing_line)
            closing_suffix = substr(closing_line, closing_length + 1)
            if (closing_length >= fence_length && closing_suffix ~ /^[[:space:]]*$/) {
              in_fence = 0
            }
            next
          }

          started_in_comment = in_comment
          has_comment_marker = 0
          remainder = line

          while (length(remainder) > 0) {
            if (in_comment) {
              close_position = index(remainder, "-->")
              if (close_position == 0) {
                remainder = ""
              } else {
                has_comment_marker = 1
                in_comment = 0
                remainder = substr(remainder, close_position + 3)
              }
            } else {
              open_position = index(remainder, "<!--")
              if (open_position == 0) {
                remainder = ""
              } else {
                has_comment_marker = 1
                in_comment = 1
                remainder = substr(remainder, open_position + 4)
              }
            }
          }

          if (!started_in_comment && !has_comment_marker) {
            fence_line = line
            sub(/^[[:space:]]*/, "", fence_line)
            opening_character = substr(fence_line, 1, 1)
            if (opening_character == "`" || opening_character == "~") {
              opening_length = leading_fence_length(line, opening_character)
              opening_suffix = substr(fence_line, opening_length + 1)
              valid_opening = opening_length >= 3
              if (opening_character == "`" && index(opening_suffix, "`") != 0) {
                valid_opening = 0
              }
              if (valid_opening) {
                in_fence = 1
                fence_character = opening_character
                fence_length = opening_length
                next
              }
            }

            if (line == acknowledgement) {
              found = 1
            }
          }
        }
        END {
          print found ? "true" : "false"
        }
      ')
      ;;
  esac
fi

printf 'has-breaking-changes=%s\n' "${has_breaking_changes}"
printf 'approved=%s\n' "${approved}"

if [[ "${has_breaking_changes}" == true ]]; then
  printf 'Breaking Change Guard: breaking-change commit(s) detected; acknowledgement present: %s.\n' \
    "${approved}" >&2
fi
