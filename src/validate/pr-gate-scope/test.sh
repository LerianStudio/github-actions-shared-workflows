#!/usr/bin/env bash

# Exercises resolve.sh against a stubbed `gh`. The stub is driven by GH_PR_* and
# GH_LABELS, so every case is a pure function of its inputs and no network or
# repository fixture is involved.

set -euo pipefail

CDPATH=''
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
RESOLVER="${SCRIPT_DIR}/resolve.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/pr-gate-scope.XXXXXX")
PASSED=0
FAILED=0

cleanup() {
  rm -rf "${TEST_ROOT}"
}
trap cleanup EXIT INT TERM

if [[ ! -f "${RESOLVER}" ]]; then
  printf 'not ok - production resolver is missing: %s\n' "${RESOLVER}" >&2
  exit 1
fi

# ----------------- Stubs -----------------
mkdir -p "${TEST_ROOT}/bin"
cat > "${TEST_ROOT}/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$*" in
  *labels*) [ -n "${GH_LABELS:-}" ] && printf '%s\n' ${GH_LABELS} ; true ;;
  *baseRefName*) printf '%s %s %s %s\n' "${GH_PR_BASE}" "${GH_PR_HEAD}" "${GH_PR_SHA}" "${GH_PR_AUTHOR}" ;;
  *) printf 'unexpected gh call: %s\n' "$*" >&2; exit 1 ;;
esac
STUB
chmod +x "${TEST_ROOT}/bin/gh"
PATH="${TEST_ROOT}/bin:${PATH}"

# ----------------- Harness -----------------
# Usage: check <description> <expected in-scope> <expected reason substring> [VAR=value ...]
check() {
  local description=$1 expected_scope=$2 expected_reason=$3
  shift 3

  local output status
  set +e
  output=$(
    env \
      GH_TOKEN=stub \
      REPO=Lerian/example \
      PR_NUMBER=42 \
      GH_PR_BASE=develop \
      GH_PR_HEAD=feature/x \
      GH_PR_SHA=abc1234567 \
      GH_PR_AUTHOR=alice \
      GH_LABELS='' \
      SCOPE_RULES='{"develop": "*", "main": "hotfix/*"}' \
      ADDITIONAL_SCOPE_RULES='' \
      FORCE_LABELS='' \
      SKIP_LABELS='' \
      IGNORE_AUTHORS='' \
      VERBOSE=false \
      "$@" \
      bash "${RESOLVER}" 2>/dev/null
  )
  status=$?
  set -e

  local actual_scope actual_reason
  actual_scope=$(sed -n 's/^in-scope=//p' <<< "${output}")
  actual_reason=$(sed -n 's/^reason=//p' <<< "${output}")

  if [[ "${expected_scope}" == 'error' ]]; then
    if [[ ${status} -ne 0 ]]; then
      PASSED=$((PASSED + 1))
      printf 'ok - %s\n' "${description}"
    else
      FAILED=$((FAILED + 1))
      printf 'not ok - %s (expected a non-zero exit, got %s)\n' "${description}" "${status}"
    fi
    return
  fi

  if [[ ${status} -ne 0 ]]; then
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (resolver exited %s)\n' "${description}" "${status}"
    return
  fi

  if [[ "${actual_scope}" != "${expected_scope}" ]]; then
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (in-scope: expected %s, got %s)\n' \
      "${description}" "${expected_scope}" "${actual_scope}"
    return
  fi

  if [[ -n "${expected_reason}" && "${actual_reason}" != *"${expected_reason}"* ]]; then
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (reason: expected to contain %s, got %s)\n' \
      "${description}" "${expected_reason}" "${actual_reason}"
    return
  fi

  PASSED=$((PASSED + 1))
  printf 'ok - %s\n' "${description}"
}

# ----------------- Base to head rules -----------------
check 'anything into develop is in scope' true "rule develop <- '*'"
check 'hotfix into main is in scope' true "rule main <- 'hotfix/*'" \
  GH_PR_BASE=main GH_PR_HEAD=hotfix/urgent
check 'a feature into main is not' false 'no rule matches' \
  GH_PR_BASE=main GH_PR_HEAD=feature/x
check 'a base absent from the rules is never in scope' false 'no rule matches' \
  GH_PR_BASE=release-candidate GH_PR_HEAD=develop
check 'a glob matches a nested branch name' true "rule main <- 'hotfix/*'" \
  GH_PR_BASE=main GH_PR_HEAD=hotfix/team/urgent
check 'a glob does not match a sibling prefix' false 'no rule matches' \
  GH_PR_BASE=main GH_PR_HEAD=hotfixes/urgent

# ----------------- additional-scope-rules -----------------
check 'an additional base is added' true "rule release-candidate <- 'develop'" \
  GH_PR_BASE=release-candidate GH_PR_HEAD=develop \
  ADDITIONAL_SCOPE_RULES='{"release-candidate": "develop|hotfix/*"}'
check 'an additional rule replaces the base it names' false 'no rule matches' \
  GH_PR_BASE=develop GH_PR_HEAD=feature/x \
  ADDITIONAL_SCOPE_RULES='{"develop": "hotfix/*"}'
check 'replacing one base leaves the others alone' true "rule main <- 'hotfix/*'" \
  GH_PR_BASE=main GH_PR_HEAD=hotfix/x \
  ADDITIONAL_SCOPE_RULES='{"develop": "hotfix/*"}'

# ----------------- Label overrides -----------------
check 'a force label overrides the rules' true "force label 'breaking-change-review'" \
  GH_PR_BASE=main GH_PR_HEAD=feature/x \
  GH_LABELS='breaking-change-review' FORCE_LABELS='breaking-change-review'
check 'a force label is matched case-insensitively' true 'force label' \
  GH_PR_BASE=main GH_PR_HEAD=feature/x \
  GH_LABELS='Breaking-Change-Review' FORCE_LABELS='breaking-change-review'
check 'a force label does not fire when a rule already matched' true 'rule develop' \
  GH_LABELS='breaking-change-review' FORCE_LABELS='breaking-change-review'
check 'a skip label removes a matching pull request' false "skip label 'exempt'" \
  GH_LABELS='exempt' SKIP_LABELS='exempt'
check 'a skip label beats a force label' false 'skip label' \
  GH_PR_BASE=main GH_PR_HEAD=feature/x \
  GH_LABELS='exempt breaking-change-review' \
  SKIP_LABELS='exempt' FORCE_LABELS='breaking-change-review'
check 'an undeclared skip label changes nothing' true 'rule develop' \
  GH_LABELS='something-else' SKIP_LABELS='exempt'

# ----------------- Author veto -----------------
check 'an ignored author vetoes a matching rule' false 'ignored author' \
  GH_PR_AUTHOR='dependabot[bot]' IGNORE_AUTHORS='dependabot[bot]'
check 'the app/ spelling is the same entry' false 'ignored author' \
  GH_PR_AUTHOR='app/dependabot' IGNORE_AUTHORS='dependabot[bot]'
check 'the bare spelling is the same entry' false 'ignored author' \
  GH_PR_AUTHOR='dependabot[bot]' IGNORE_AUTHORS='dependabot'
check 'the author veto beats a force label' false 'ignored author' \
  GH_PR_BASE=main GH_PR_HEAD=feature/x GH_PR_AUTHOR='dependabot[bot]' \
  GH_LABELS='breaking-change-review' \
  FORCE_LABELS='breaking-change-review' IGNORE_AUTHORS='dependabot[bot]'
check 'a login that is not listed is unaffected' true 'rule develop' \
  GH_PR_AUTHOR=alice IGNORE_AUTHORS='dependabot[bot]'
check 'whitespace around commas is tolerated' false 'ignored author' \
  GH_PR_AUTHOR=bob IGNORE_AUTHORS='alice, bob , carol'

# ----------------- Fails closed -----------------
check 'a malformed scope-rules object is an error' error '' \
  SCOPE_RULES='not json'
check 'a scope-rules array is an error' error '' \
  SCOPE_RULES='["develop"]'
check 'a non-string rule value is an error' error '' \
  SCOPE_RULES='{"develop": ["*"]}'
check 'a malformed additional-scope-rules object is an error' error '' \
  ADDITIONAL_SCOPE_RULES='{"develop"}'
check 'a missing pull request number is an error' error '' \
  PR_NUMBER=''
check 'pull request number zero is an error' error '' \
  PR_NUMBER=0

# ----------------- Reported facts -----------------
reported=$(
  env GH_TOKEN=stub REPO=Lerian/example PR_NUMBER=7 \
    GH_PR_BASE=main GH_PR_HEAD=hotfix/x GH_PR_SHA=deadbeef GH_PR_AUTHOR=alice \
    GH_LABELS='' SCOPE_RULES='{"main": "hotfix/*"}' ADDITIONAL_SCOPE_RULES='' \
    FORCE_LABELS='' SKIP_LABELS='' IGNORE_AUTHORS='' VERBOSE=false \
    bash "${RESOLVER}" 2>/dev/null
)
for expected in 'pr-number=7' 'base-ref=main' 'head-ref=hotfix/x' 'head-sha=deadbeef' 'author=alice'; do
  if grep -qx -- "${expected}" <<< "${reported}"; then
    PASSED=$((PASSED + 1))
    printf 'ok - reports %s\n' "${expected}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - reports %s\n' "${expected}"
  fi
done

printf '\n%s passed, %s failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
