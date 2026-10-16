#!/usr/bin/env bash

# Exercises resolve.sh against a stubbed `gh` serving a canned commit list.

set -euo pipefail

CDPATH=''
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
RESOLVER="${SCRIPT_DIR}/resolve.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/breaking-change-commits.XXXXXX")
PASSED=0
FAILED=0

cleanup() { rm -rf "${TEST_ROOT}"; }
trap cleanup EXIT INT TERM

mkdir -p "${TEST_ROOT}/bin"
cat > "${TEST_ROOT}/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$*" in
  *"/commits"*) printf '%s\n' ${COMMITS_B64} ;;
  *) exit 1 ;;
esac
STUB
chmod +x "${TEST_ROOT}/bin/gh"
PATH="${TEST_ROOT}/bin:${PATH}"

# encode <sha> <message>
encode() {
  jq -cn --arg s "$1" --arg m "$2" '[$s, $m]' | base64 | tr -d '\n'
}

# `|| true` so a resolver that exits non-zero is reported as a failing case
# rather than aborting the suite at the assignment, which under `set -e` would
# take the summary line with it and never name the case that broke.
run() {
  env GH_TOKEN=stub REPO=LerianStudio/example PR_NUMBER=42 COMMITS_B64="$1" \
    bash "${RESOLVER}" 2>/dev/null || true
}

check() {
  local description=$1 commits=$2 expected_count=$3 expected_shas=$4
  local output count shas
  output=$(run "${commits}")
  count=$(sed -n 's/^count=//p' <<< "${output}")
  shas=$(sed -n 's/^shas=//p' <<< "${output}")

  if [[ "${count}" == "${expected_count}" && "${shas}" == "${expected_shas}" ]]; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${description}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (count=%s shas=%s; wanted %s / %s)\n' \
      "${description}" "${count}" "${shas}" "${expected_count}" "${expected_shas}"
  fi
}

BANG=$(encode aaa1111 'feat(scope)!: breaks the contract')
PLAIN=$(encode bbb2222 'fix(scope): ordinary work')
FOOTER=$(encode ccc3333 'feat(scope): looks ordinary

BREAKING CHANGE: the field was removed')
BULLET=$(encode ddd4444 'refactor: cleanup

* BREAKING CHANGE: moved')
HYPHEN=$(encode eee5555 'refactor: cleanup

BREAKING-CHANGE: moved')
PROSE=$(encode fff6666 'docs: explain the policy

We document how a BREAKING CHANGE is handled here.')
NOTYPE=$(encode aaa7777 '!: no type at all')

check 'a bang subject is breaking' "${BANG}" 1 aaa1111
check 'an ordinary commit is not' "${PLAIN}" 0 ''
check 'a BREAKING CHANGE footer is breaking' "${FOOTER}" 1 ccc3333
check 'a bullet-prefixed footer is breaking' "${BULLET}" 1 ddd4444
check 'BREAKING-CHANGE with a hyphen is not' "${HYPHEN}" 0 ''
check 'prose mentioning the phrase mid-line is not' "${PROSE}" 0 ''
check 'a bang with no type is breaking' "${NOTYPE}" 1 aaa7777
check 'several breaking commits are all listed' "${BANG} ${PLAIN} ${FOOTER}" 2 aaa1111,ccc3333
check 'order follows the commit list' "${FOOTER} ${BANG}" 2 ccc3333,aaa1111

# ----------------- Parity with the detector -----------------
# The detector lowercases before matching, and allows any scope content. These
# are the forms where a transcription slip would make this view disagree with
# the verdict.
LOWER=$(encode aab1111 'feat(scope): looks ordinary

breaking change: lowercase footer')
MIXED=$(encode aab2222 'feat(scope): looks ordinary

Breaking Change: mixed case footer')
PLURAL=$(encode aab3333 'feat(scope): looks ordinary

BREAKING CHANGES: plural')
SPACED=$(encode aab4444 'feat(scope): looks ordinary

BREAKING CHANGE the separator is a space')
NESTED=$(encode aab5555 'feat(a)b)!: a scope containing a closing paren')
UPPER_SUBJECT=$(encode aab6666 'FEAT(SCOPE)!: an uppercase subject')

check 'a lowercase footer is breaking' "${LOWER}" 1 aab1111
check 'a mixed-case footer is breaking' "${MIXED}" 1 aab2222
check 'the plural form is breaking' "${PLURAL}" 1 aab3333
check 'a space separator is breaking' "${SPACED}" 1 aab4444
check 'a scope containing a paren still matches' "${NESTED}" 1 aab5555
check 'an uppercase subject is breaking' "${UPPER_SUBJECT}" 1 aab6666

# ----------------- Output injection -----------------
# The subjects are commit-controlled and go into GITHUB_OUTPUT as a multiline
# value. A fixed delimiter would let a commit close the block and write its own
# assignments — `fingerprint=` among them, which decides whether this change
# counts as already approved.
INJECT_CLOSE=$(encode aac1111 'BREAKING_SUBJECTS_EOF

BREAKING CHANGE: closes the block above')
INJECT_VALUE=$(encode aac2222 'fingerprint=deadbeefdeadbeef

BREAKING CHANGE: and assigns a forged one')

# Parsed the way the runner parses GITHUB_OUTPUT: lines inside a multiline
# block are a value, not assignments. Grepping the raw text would find the
# forged line sitting harmlessly inside the block and call it a breach.
single_line_assignments() {
  local line delimiter='' in_block=0
  while IFS= read -r line; do
    if [[ ${in_block} -eq 1 ]]; then
      [[ "${line}" == "${delimiter}" ]] && in_block=0
      continue
    fi
    if [[ "${line}" == *'<<'* ]]; then
      delimiter=${line#*<<}
      in_block=1
      continue
    fi
    printf '%s\n' "${line}"
  done
}

injected=$(run "${INJECT_CLOSE} ${INJECT_VALUE}")
forged=$(single_line_assignments <<< "${injected}" \
  | grep -c '^fingerprint=deadbeefdeadbeef$' || true)
if [[ "${forged}" == '0' ]]; then
  PASSED=$((PASSED + 1))
  printf 'ok - a commit subject cannot close the output block and forge a value\n'
else
  FAILED=$((FAILED + 1))
  printf 'not ok - a commit subject forged an output assignment\n'
fi

# ----------------- Fingerprint -----------------
fingerprint_of() { run "$1" | sed -n 's/^fingerprint=//p'; }

same_a=$(fingerprint_of "${BANG} ${PLAIN}")
same_b=$(fingerprint_of "${BANG} ${PLAIN}")
added=$(fingerprint_of "${BANG} ${PLAIN} ${FOOTER}")
ordinary_added=$(fingerprint_of "${BANG} ${PLAIN} ${PLAIN}")
none=$(fingerprint_of "${PLAIN}")

assert() {
  if [[ "$2" == "$3" ]]; then
    PASSED=$((PASSED + 1)); printf 'ok - %s\n' "$1"
  else
    FAILED=$((FAILED + 1)); printf 'not ok - %s (%s vs %s)\n' "$1" "$2" "$3"
  fi
}
refute() {
  if [[ "$2" != "$3" ]]; then
    PASSED=$((PASSED + 1)); printf 'ok - %s\n' "$1"
  else
    FAILED=$((FAILED + 1)); printf 'not ok - %s (both %s)\n' "$1" "$2"
  fi
}

assert 'the same set fingerprints the same' "${same_a}" "${same_b}"
assert 'adding an ordinary commit does not change it' "${same_a}" "${ordinary_added}"
refute 'adding a breaking commit changes it' "${same_a}" "${added}"
assert 'no breaking commits means no fingerprint' "${none}" ''

printf '\n%s passed, %s failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
