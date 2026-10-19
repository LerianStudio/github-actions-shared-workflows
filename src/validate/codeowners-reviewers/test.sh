#!/usr/bin/env bash

# Exercises resolve.sh against a stubbed `gh` that serves CODEOWNERS content
# from CODEOWNERS_BODY, for whichever path CODEOWNERS_AT names.

set -euo pipefail

CDPATH=''
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
RESOLVER="${SCRIPT_DIR}/resolve.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/codeowners-reviewers.XXXXXX")
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

mkdir -p "${TEST_ROOT}/bin"
cat > "${TEST_ROOT}/bin/gh" <<'STUB'
#!/usr/bin/env bash
want=${CODEOWNERS_AT:-.github/CODEOWNERS}
for arg in "$@"; do
  case "$arg" in
    *"/contents/${want}"*) printf '%s\n' "${CODEOWNERS_BODY}"; exit 0 ;;
  esac
done
exit 1
STUB
chmod +x "${TEST_ROOT}/bin/gh"
PATH="${TEST_ROOT}/bin:${PATH}"

# Usage: check <description> <expected found> <expected reviewers> [VAR=value ...]
check() {
  local description=$1 expected_found=$2 expected_reviewers=$3
  shift 3

  local output
  output=$(
    env GH_TOKEN=stub REPO=LerianStudio/example REF='' PATTERN='*' MAX_REVIEWERS=6 \
      CODEOWNERS_AT='.github/CODEOWNERS' "$@" \
      bash "${RESOLVER}" 2>/dev/null
  )

  local found reviewers
  found=$(sed -n 's/^found=//p' <<< "${output}")
  reviewers=$(sed -n 's/^reviewers=//p' <<< "${output}")

  if [[ "${found}" == "${expected_found}" && "${reviewers}" == "${expected_reviewers}" ]]; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${description}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (found=%s reviewers=%s; wanted found=%s reviewers=%s)\n' \
      "${description}" "${found}" "${reviewers}" "${expected_found}" "${expected_reviewers}"
  fi
}

check 'a team owner becomes team:<slug>' true 'team:g_github_devops' \
  CODEOWNERS_BODY='*    @LerianStudio/g_github_devops'
check 'a user owner becomes user:<login>' true 'user:bedatty' \
  CODEOWNERS_BODY='* @bedatty'
check 'several owners are kept in order' true 'team:devops,user:bedatty' \
  CODEOWNERS_BODY='* @LerianStudio/devops @bedatty'
check 'comments and blank lines are ignored' true 'team:devops' \
  CODEOWNERS_BODY='# owners
# of everything

*   @LerianStudio/devops'
check 'a trailing comment is stripped' true 'team:devops' \
  CODEOWNERS_BODY='* @LerianStudio/devops # the devops team'
check 'only the catch-all rule is read' true 'team:owners' \
  CODEOWNERS_BODY='/docs/ @LerianStudio/writers
* @LerianStudio/owners
/src/ @LerianStudio/engineers'
check 'the last catch-all wins, as CODEOWNERS resolves it' true 'team:second' \
  CODEOWNERS_BODY='* @LerianStudio/first
* @LerianStudio/second'
check 'a specific pattern can be asked for' true 'team:writers' \
  PATTERN='/docs/' \
  CODEOWNERS_BODY='/docs/ @LerianStudio/writers
* @LerianStudio/owners'
check 'enterprise section headers are not patterns' true 'team:owners' \
  CODEOWNERS_BODY='[Everything]
* @LerianStudio/owners'
check 'a caret section header is not a pattern either' true 'team:owners' \
  CODEOWNERS_BODY='^[Optional]
* @LerianStudio/owners'
check 'duplicate owners collapse' true 'team:devops' \
  CODEOWNERS_BODY='* @LerianStudio/devops @LerianStudio/devops'
check 'emails are dropped, the rest is kept' true 'team:devops' \
  CODEOWNERS_BODY='* @LerianStudio/devops someone@example.com'
check 'an owners-only email list yields nothing' false '' \
  CODEOWNERS_BODY='* someone@example.com'
check 'no catch-all rule yields nothing' false '' \
  CODEOWNERS_BODY='/src/ @LerianStudio/engineers'
check 'a rule with no owner is skipped' false '' \
  CODEOWNERS_BODY='*'
check 'an empty CODEOWNERS yields nothing' false '' \
  CODEOWNERS_BODY=''
check 'a missing CODEOWNERS yields nothing' false '' \
  CODEOWNERS_AT='nowhere' CODEOWNERS_BODY='* @LerianStudio/devops'
check 'the root location is used as a fallback' true 'team:devops' \
  CODEOWNERS_AT='CODEOWNERS' CODEOWNERS_BODY='* @LerianStudio/devops'
check 'the docs location is used as a fallback' true 'team:devops' \
  CODEOWNERS_AT='docs/CODEOWNERS' CODEOWNERS_BODY='* @LerianStudio/devops'
check 'more than six reviewers are capped' true 'user:a,user:b,user:c,user:d,user:e,user:f' \
  CODEOWNERS_BODY='* @a @b @c @d @e @f @g @h'
check 'the cap is configurable' true 'user:a,user:b' \
  MAX_REVIEWERS=2 CODEOWNERS_BODY='* @a @b @c'

# The source is reported so a caller can say where the reviewers came from.
source_line=$(
  env GH_TOKEN=stub REPO=LerianStudio/example REF='' PATTERN='*' MAX_REVIEWERS=6 \
    CODEOWNERS_AT='docs/CODEOWNERS' CODEOWNERS_BODY='* @LerianStudio/devops' \
    bash "${RESOLVER}" 2>/dev/null | sed -n 's/^source=//p'
)
if [[ "${source_line}" == 'docs/CODEOWNERS' ]]; then
  PASSED=$((PASSED + 1))
  printf 'ok - reports which CODEOWNERS it read\n'
else
  FAILED=$((FAILED + 1))
  printf 'not ok - reports which CODEOWNERS it read (got %s)\n' "${source_line}"
fi

printf '\n%s passed, %s failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
