#!/usr/bin/env bash

# Runs the decision step of .github/workflows/coderabbit-gate.yml as written, under
# the runner's own shell flags and with a stub `gh` on PATH, and asserts for which
# authors it posts `@coderabbitai review`. No network, no GitHub.

set -euo pipefail

CDPATH=''
WORKFLOW="$(cd -- "$(dirname -- "$0")/../.." && pwd)/.github/workflows/coderabbit-gate.yml"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/coderabbit-gate.XXXXXX")
trap 'rm -rf "${WORK_DIR}"' EXIT INT TERM
PASSED=0
FAILED=0

# The job has a single step: print its `run: |` body dedented to column zero.
awk '
  !inrun && /^[[:space:]]*run: \|[[:space:]]*$/ { match($0, /^ */); indent = RLENGTH; inrun = 1; next }
  inrun {
    if ($0 ~ /^[[:space:]]*$/) { print ""; next }
    match($0, /^ */)
    if (RLENGTH <= indent) exit
    print substr($0, indent + 3)
  }
' "${WORKFLOW}" >"${WORK_DIR}/gate.sh"
[[ -s ${WORK_DIR}/gate.sh ]] || {
  printf 'not ok - could not extract the run block from %s\n' "${WORKFLOW}" >&2
  exit 1
}

# `gh pr view` answers with an in-scope, green pull request opened by STUB_AUTHOR;
# `gh pr comment` is recorded; every other call succeeds and prints nothing.
mkdir "${WORK_DIR}/bin"
cat >"${WORK_DIR}/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$1 $2" in
  'pr view') printf 'develop feat/x abc123 %s\n' "${STUB_AUTHOR}" ;;
  'pr comment') printf '%s\n' "$*" >>"${STUB_COMMENTS}" ;;
esac
STUB
chmod +x "${WORK_DIR}/bin/gh"

# assert <label> <author> <ignore_authors> <RADAGAST_AUTHORS> <review|skip> [notice text]
assert() {
  local label=$1 author=$2 ignore=$3 radagast=$4 expected=$5 notice=${6:-}
  local comments="${WORK_DIR}/comments" out got=skip

  : >"${comments}"
  if ! out=$(PATH="${WORK_DIR}/bin:${PATH}" STUB_AUTHOR="${author}" STUB_COMMENTS="${comments}" \
    REPO=acme/widget PR_NUMBER=7 CHECKS_PASSED=true HEAD_SHA=abc123 \
    REVIEW_BASE_BRANCHES=develop REVIEW_HEAD_PATTERNS='hotfix/*' LABEL='' DRY_RUN=false \
    IGNORE_AUTHORS="${ignore}" RADAGAST_AUTHORS="${radagast}" \
    bash --noprofile --norc -eo pipefail "${WORK_DIR}/gate.sh" 2>&1); then
    FAILED=$((FAILED + 1))
    printf 'not ok - %s: the step exited non-zero: %s\n' "${label}" "${out}" >&2
    return
  fi

  grep -q '@coderabbitai review' "${comments}" && got=review
  if [[ ${got} != "${expected}" ]]; then
    FAILED=$((FAILED + 1))
    printf 'not ok - %s: expected %s, got %s: %s\n' "${label}" "${expected}" "${got}" "${out}" >&2
  elif [[ -n ${notice} ]] && ! grep -qF "${notice}" <<<"${out}"; then
    FAILED=$((FAILED + 1))
    printf 'not ok - %s: expected a notice containing [%s], got: %s\n' "${label}" "${notice}" "${out}" >&2
  else
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${label}"
  fi
}

assert 'an unset variable keeps today'\''s behaviour' fredcamaral 'dependabot[bot]' '' review
assert 'a listed author is left to Radagast' fredcamaral 'dependabot[bot]' fredcamaral skip 'reviewed by Radagast'
assert 'any spelling and spacing of a listed login matches' fredcamaral '' ' alice , app/FredCamaral[bot] ' skip 'reviewed by Radagast'
assert 'an unlisted author still gets CodeRabbit' alice 'dependabot[bot]' fredcamaral review
assert 'ignore_authors still vetoes on its own' app/dependabot 'dependabot[bot]' fredcamaral skip 'an ignored author'

printf '%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
