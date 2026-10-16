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

run() {
  env GH_TOKEN=stub REPO=LerianStudio/example PR_NUMBER=42 COMMITS_B64="$1" \
    bash "${RESOLVER}" 2>/dev/null
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
