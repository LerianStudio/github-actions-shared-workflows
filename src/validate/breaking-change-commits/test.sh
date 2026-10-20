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
  # The historical path: the breaking set as it stood at a given revision,
  # which is how the gate asks what an approval actually approved. COMPARE_JSON
  # is the canned payload; COMPARE_TOTAL overrides `total_commits` to simulate
  # the same 250 cap the pull-request path has.
  *"/compare/"*)
    printf '%s' "${COMPARE_JSON:-{\"total_commits\":0,\"commits\":[]\}}" ;;
  *"/commits"*) printf '%s\n' ${COMMITS_B64} ;;
  # The declared total. DECLARED_COMMITS overrides it to simulate the 250 cap,
  # where the endpoint returns fewer commits than the pull request has.
  *"/pulls/"*)
    if [ -n "${DECLARED_COMMITS:-}" ]; then
      printf '%s\n' "${DECLARED_COMMITS}"
    else
      printf '%s\n' ${COMMITS_B64} | grep -c . || true
    fi ;;
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

# compare_payload <total> <sha> <message> [<sha> <message> ...]
compare_payload() {
  local total=$1; shift
  local entries=''
  while [[ $# -gt 0 ]]; do
    entries="${entries:+${entries},}$(jq -cn --arg s "$1" --arg m "$2" \
      '{sha: $s, commit: {message: $m}}')"
    shift 2
  done
  printf '{"total_commits":%s,"commits":[%s]}' "${total}" "${entries}"
}

run_at_sha() {
  env GH_TOKEN=stub REPO=LerianStudio/example PR_NUMBER=42 \
    BASE_REF=develop AT_SHA="$1" COMPARE_JSON="$2" COMMITS_B64='' \
    bash "${RESOLVER}" 2>/dev/null || true
}

check_at_sha() {
  local description=$1 payload=$2 expected_count=$3
  local output count
  output=$(run_at_sha aaaa111 "${payload}")
  count=$(sed -n 's/^count=//p' <<< "${output}")

  if [[ "${count}" == "${expected_count}" ]]; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${description}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (count=%s; wanted %s)\n' \
      "${description}" "${count}" "${expected_count}"
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

# ----------------- The 250-commit cap -----------------
# The endpoint returns at most 250 commits however much you paginate. Answering
# from a truncated list reports "no breaking change" for a break living past the
# cap — and, with approval reuse, leaves the fingerprint unchanged while the
# change gained a break nobody approved.
# `|| capped_status=$?` on the assignment itself: under `set -e` a command
# substitution that exits non-zero takes the script down before the next line
# can read `$?`. This is the same trap the `run` helper above already sidesteps.
capped_status=0
capped=$(
  env GH_TOKEN=stub REPO=LerianStudio/example PR_NUMBER=42 \
    COMMITS_B64="${PLAIN}" DECLARED_COMMITS=300 \
    bash "${RESOLVER}" 2>/dev/null
) || capped_status=$?
if [[ ${capped_status} -ne 0 && -z "${capped}" ]]; then
  PASSED=$((PASSED + 1))
  printf 'ok - an incomplete enumeration is refused, not answered\n'
else
  FAILED=$((FAILED + 1))
  printf 'not ok - a truncated commit list produced a verdict (%s)\n' "${capped}"
fi

complete=$(
  env GH_TOKEN=stub REPO=LerianStudio/example PR_NUMBER=42 \
    COMMITS_B64="${BANG} ${PLAIN}" DECLARED_COMMITS=2 \
    bash "${RESOLVER}" 2>/dev/null | sed -n 's/^count=//p'
)
if [[ "${complete}" == '1' ]]; then
  PASSED=$((PASSED + 1))
  printf 'ok - a complete enumeration is answered normally\n'
else
  FAILED=$((FAILED + 1))
  printf 'not ok - a complete enumeration was refused (count=%s)\n' "${complete}"
fi

# --- resolving at a past revision -------------------------------------------
# The gate asks "what did that approval approve?" and the only honest answer
# comes from the approving run's own head. Believing the fingerprint written in
# a comment is what let a member reuse somebody else's approval.
check_at_sha 'a past revision is resolved from the comparison' \
  "$(compare_payload 2 aaa1111 'feat(scope)!: breaks the contract' \
                       bbb2222 'fix(scope): ordinary work')" 1
check_at_sha 'a past revision with nothing breaking' \
  "$(compare_payload 1 bbb2222 'fix(scope): ordinary work')" 0
check_at_sha 'the footer form counts there too' \
  "$(compare_payload 1 ccc3333 'feat(scope): looks ordinary

BREAKING CHANGE: the field was removed')" 1

# The same cap, and the same refusal. Answering from a truncated comparison
# would let an omitted breaking commit leave the fingerprint unchanged.
truncated=$(run_at_sha aaaa111 "$(compare_payload 300 aaa1111 'feat(scope)!: breaks')")
if [[ -z "$(sed -n 's/^count=//p' <<< "${truncated}")" ]]; then
  PASSED=$((PASSED + 1))
  printf 'ok - a truncated comparison is refused\n'
else
  FAILED=$((FAILED + 1))
  printf 'not ok - a truncated comparison produced a verdict (%s)\n' "${truncated}"
fi

# Two revisions of the same pull request: the fingerprint has to differ once a
# breaking commit is added, or reuse cannot tell them apart.
fp_before=$(
  run_at_sha aaaa111 "$(compare_payload 1 aaa1111 'feat(scope)!: breaks')" \
    | sed -n 's/^fingerprint=//p'
)
fp_after=$(
  run_at_sha bbbb222 "$(compare_payload 2 aaa1111 'feat(scope)!: breaks' \
                                          ddd4444 'feat(other)!: breaks too')" \
    | sed -n 's/^fingerprint=//p'
)
if [[ -n "${fp_before}" && -n "${fp_after}" && "${fp_before}" != "${fp_after}" ]]; then
  PASSED=$((PASSED + 1))
  printf 'ok - adding a breaking commit changes the fingerprint\n'
else
  FAILED=$((FAILED + 1))
  printf 'not ok - the fingerprint did not change (%s vs %s)\n' "${fp_before}" "${fp_after}"
fi

# And AT_SHA without a base cannot silently fall back to the current head.
if ! env GH_TOKEN=stub REPO=LerianStudio/example PR_NUMBER=42 \
     AT_SHA=aaaa111 COMMITS_B64='' bash "${RESOLVER}" >/dev/null 2>&1; then
  PASSED=$((PASSED + 1))
  printf 'ok - AT_SHA without BASE_REF is refused\n'
else
  FAILED=$((FAILED + 1))
  printf 'not ok - AT_SHA without BASE_REF was accepted\n'
fi

printf '\n%s passed, %s failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
