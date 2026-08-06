#!/usr/bin/env bash

set -euo pipefail

CDPATH=''
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
DETECTOR="${SCRIPT_DIR}/detect.sh"
REAL_GIT=$(command -v git)
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/breaking-change-guard.XXXXXX")
CURRENT_REPO=
CURRENT_REMOTE=
AWK_BIN='awk'
PASSED=0
FAILED=0

cleanup() {
  rm -rf "${TEST_ROOT}"
}
trap cleanup EXIT INT TERM

if [[ ! -f "${DETECTOR}" ]]; then
  printf 'not ok - production detector is missing: %s\n' "${DETECTOR}" >&2
  exit 1
fi

new_repo() {
  local name=$1
  local remote="${TEST_ROOT}/${AWK_BIN}-${name}-remote.git"
  local repo="${TEST_ROOT}/${AWK_BIN}-${name}"

  git init -q --bare "${remote}"
  git --git-dir="${remote}" config core.hooksPath /dev/null
  git init -q "${repo}"
  git -C "${repo}" config user.name "Breaking Change Guard Test"
  git -C "${repo}" config user.email "breaking-change-guard@example.com"
  git -C "${repo}" config commit.gpgSign false
  git -C "${repo}" config core.hooksPath /dev/null
  git -C "${repo}" checkout -q -b main
  git -C "${repo}" commit -q --allow-empty -m "chore: initial commit"
  git -C "${repo}" remote add origin "${remote}"
  git -C "${repo}" push -q -u origin main
  git -C "${repo}" checkout -q -b feature
  CURRENT_REPO=${repo}
  CURRENT_REMOTE=${remote}
}

make_shallow_clone_without_parent() {
  local name=$1
  local repo="${TEST_ROOT}/${AWK_BIN}-${name}-shallow"
  local is_shallow

  git -C "${CURRENT_REPO}" push -q origin feature
  git clone -q --depth 1 --branch feature "file://${CURRENT_REMOTE}" "${repo}"
  git -C "${repo}" config commit.gpgSign false
  git -C "${repo}" config core.hooksPath /dev/null
  git -C "${repo}" fetch -q --depth=1 origin main:refs/remotes/origin/main

  is_shallow=$(git -C "${repo}" rev-parse --is-shallow-repository)
  if [[ "${is_shallow}" != true ]]; then
    printf 'fixture error - expected a shallow repository\n' >&2
    exit 1
  fi
  if git -C "${repo}" cat-file -e 'HEAD^' 2>/dev/null; then
    printf 'fixture error - shallow clone unexpectedly contains the older breaking commit\n' >&2
    exit 1
  fi

  CURRENT_REPO=${repo}
}

commit_message() {
  git -C "${CURRENT_REPO}" commit -q --allow-empty --cleanup=verbatim -m "$1"
}

record_pass() {
  PASSED=$((PASSED + 1))
  printf 'ok - %s [%s]\n' "$1" "${AWK_BIN}"
}

record_fail() {
  FAILED=$((FAILED + 1))
  printf 'not ok - %s [%s]: %s\n' "$1" "${AWK_BIN}" "$2" >&2
}

assert_guard() {
  local label=$1
  local expected_breaking=$2
  local expected_approved=$3
  local body=$4
  local acknowledgement=$5
  local base_ref=${6:-main}
  local command_path=${7:-${PATH}}
  local match_mode=${8:-contains}
  local stdout_file="${TEST_ROOT}/stdout"
  local stderr_file="${TEST_ROOT}/stderr"
  local expected_file="${TEST_ROOT}/expected"
  local expected
  local actual
  local status

  expected=$(printf 'has-breaking-changes=%s\napproved=%s' \
    "${expected_breaking}" "${expected_approved}")
  printf '%s\n' "${expected}" >"${expected_file}"

  if (
    cd "${CURRENT_REPO}" || exit 99
    PATH="${command_path}" BASE_REF="${base_ref}" PR_BODY="${body}" \
      ACK="${acknowledgement}" ACKNOWLEDGEMENT_MATCH_MODE="${match_mode}" \
      AWK="${AWK_BIN}" bash "${DETECTOR}"
  ) >"${stdout_file}" 2>"${stderr_file}"; then
    status=0
  else
    status=$?
  fi

  actual=$(<"${stdout_file}")
  if [[ ${status} -ne 0 ]]; then
    record_fail "${label}" "expected exit 0, got ${status}: $(<"${stderr_file}")"
  elif ! cmp -s "${expected_file}" "${stdout_file}"; then
    record_fail "${label}" "expected [${expected}], got [${actual}]"
  else
    record_pass "${label}"
  fi
}

assert_runtime_failure() {
  local label=$1
  local expected_stderr=$2
  local base_ref=${3:-main}
  local command_path=${4:-${PATH}}
  local stdout_file="${TEST_ROOT}/stdout"
  local stderr_file="${TEST_ROOT}/stderr"
  local expected_stderr_file="${TEST_ROOT}/expected-stderr"
  local status

  printf '%s\n' "${expected_stderr}" >"${expected_stderr_file}"

  if (
    cd "${CURRENT_REPO}" || exit 99
    PATH="${command_path}" BASE_REF="${base_ref}" PR_BODY="" ACK="" \
      ACKNOWLEDGEMENT_MATCH_MODE=contains AWK="${AWK_BIN}" bash "${DETECTOR}"
  ) >"${stdout_file}" 2>"${stderr_file}"; then
    status=0
  else
    status=$?
  fi

  if [[ ${status} -eq 0 ]]; then
    record_fail "${label}" "expected a nonzero exit, got output [$(<"${stdout_file}")]"
  elif [[ -s "${stdout_file}" ]]; then
    record_fail "${label}" "runtime failure emitted machine-safe output [$(<"${stdout_file}")]"
  elif [[ ! -s "${stderr_file}" ]]; then
    record_fail "${label}" "runtime failure did not emit a diagnostic"
  elif ! cmp -s "${expected_stderr_file}" "${stderr_file}"; then
    record_fail "${label}" \
      "expected stderr [${expected_stderr}], got [$(<"${stderr_file}")]"
  else
    record_pass "${label}"
  fi
}

assert_match_mode_failure() {
  local label=$1
  local match_mode=$2
  local stdout_file="${TEST_ROOT}/stdout"
  local stderr_file="${TEST_ROOT}/stderr"
  local expected_stderr_file="${TEST_ROOT}/expected-stderr"
  local expected_stderr='Breaking Change Guard: ACKNOWLEDGEMENT_MATCH_MODE must be one of: contains, exact-visible-line.'
  local status

  printf '%s\n' "${expected_stderr}" >"${expected_stderr_file}"

  if (
    cd "${CURRENT_REPO}" || exit 99
    BASE_REF=main PR_BODY="Approved for major release." \
      ACK="Approved for major release." ACKNOWLEDGEMENT_MATCH_MODE="${match_mode}" \
      AWK="${AWK_BIN}" bash "${DETECTOR}"
  ) >"${stdout_file}" 2>"${stderr_file}"; then
    status=0
  else
    status=$?
  fi

  if [[ ${status} -eq 0 ]]; then
    record_fail "${label}" "expected a nonzero exit, got output [$(<"${stdout_file}")]"
  elif [[ -s "${stdout_file}" ]]; then
    record_fail "${label}" "mode failure emitted machine-safe output [$(<"${stdout_file}")]"
  elif ! cmp -s "${expected_stderr_file}" "${stderr_file}"; then
    record_fail "${label}" \
      "expected stderr [${expected_stderr}], got [$(<"${stderr_file}")]"
  else
    record_pass "${label}"
  fi
}

run_matrix() {
  local multi_ack
  local metachar_ack
  local large_body
  local wrapper_dir
  local i

  new_repo safe
  commit_message "feat: add safe behavior"
  assert_guard "ordinary safe commits" false false "No approval" "Approved"

  new_repo ordinary-scoped
  commit_message "feat(api): add safe endpoint"
  assert_guard "ordinary scoped subject" false false "" "Approved"

  new_repo type-bang-no-space
  commit_message "feat!:missing required space"
  assert_guard "type bang without required space" false false "" "Approved"

  new_repo type-bang-empty-description
  commit_message "feat!: "
  assert_guard "type bang with empty description" true false "" "Approved"

  new_repo underscore-type-bang
  commit_message "ci_pipeline!: replace pipeline"
  assert_guard "underscore type bang subject" true false "" "Approved"

  new_repo hyphen-type-bang
  commit_message "build-tools!: replace pipeline"
  assert_guard "hyphenated type bang subject" false false "" "Approved"

  new_repo nested-scope-bang
  commit_message "feat(api(v2))!: replace response"
  assert_guard "nested scope bang subject" true false "" "Approved"

  new_repo extra-description-spaces
  commit_message "feat!:  replace response"
  assert_guard "type bang with extra description spaces" true false "" "Approved"

  new_repo empty-type-bang
  commit_message "!: replace response"
  assert_guard "empty type bang subject" true false "" "Approved"

  new_repo type-bang-newest
  commit_message "fix: older safe commit"
  commit_message "feat!: remove public field"
  assert_guard "newest type bang subject" true false "" "Approved"

  new_repo type-bang-older
  commit_message "feat!: remove public field"
  commit_message "fix: newest safe commit"
  assert_guard "older type bang subject" true false "" "Approved"

  new_repo scoped-bang-newest
  commit_message "fix: older safe commit"
  commit_message "refactor(api)!: replace response schema"
  assert_guard "newest scoped type bang subject" true false "" "Approved"

  new_repo scoped-bang-older
  commit_message "refactor(api)!: replace response schema"
  commit_message "fix: newest safe commit"
  assert_guard "older scoped type bang subject" true false "" "Approved"

  new_repo breaking-change-footer
  commit_message $'feat: replace contract\n\nBREAKING CHANGE: old clients must migrate'
  assert_guard "BREAKING CHANGE footer" true false "" "Approved"

  new_repo breaking-changes-footer
  commit_message $'feat: replace contract\n\nBREAKING CHANGES: old clients must migrate'
  assert_guard "BREAKING CHANGES footer" true false "" "Approved"

  new_repo breaking-hyphen-footer
  commit_message $'feat: replace contract\n\nbreaking-change: old clients must migrate'
  assert_guard "BREAKING-CHANGE is not a release footer" false false "" "Approved"

  new_repo mixed-case-footer
  commit_message $'feat: replace contract\n\nBrEaKiNg ChAnGe: old clients must migrate'
  assert_guard "mixed-case breaking footer" true false "" "Approved"

  new_repo indented-footer
  commit_message $'feat: replace contract\n\n  BREAKING CHANGE: old clients must migrate'
  assert_guard "indented breaking footer" true false "" "Approved"

  new_repo star-footer
  commit_message $'feat: replace contract\n\n* BREAKING CHANGES old clients must migrate'
  assert_guard "star bullet and whitespace separator" true false "" "Approved"

  new_repo pipe-footer
  commit_message $'feat: replace contract\n\n| BREAKING CHANGE:: old clients must migrate'
  assert_guard "pipe bullet and repeated colon separator" true false "" "Approved"

  new_repo hyphen-bullet-footer
  commit_message $'feat: replace contract\n\n- BREAKING CHANGE: old clients must migrate'
  assert_guard "hyphen bullet is not a release note" false false "" "Approved"

  new_repo invalid-note-separator
  commit_message $'feat: replace contract\n\nBREAKING CHANGE, old clients must migrate'
  assert_guard "comma is not a release note separator" false false "" "Approved"

  new_repo prose-footer
  commit_message "docs: explain why prose mentioning BREAKING CHANGE: is not a footer"
  assert_guard "reserved footer text in prose is safe" false false "" "Approved"

  new_repo advanced-base
  commit_message "feat: safe feature commit"
  git -C "${CURRENT_REPO}" checkout -q main
  commit_message "feat!: breaking commit added only to base"
  git -C "${CURRENT_REPO}" push -q origin main
  git -C "${CURRENT_REPO}" checkout -q feature
  git -C "${CURRENT_REPO}" fetch -q origin main
  assert_guard "breaking commit only on advanced base is safe" false false "" "Approved"

  new_repo missing-base
  commit_message "feat: safe feature commit"
  assert_runtime_failure "missing base ref fails closed" \
    "Breaking Change Guard: base ref origin/missing is missing or invalid." missing

  new_repo invalid-head
  git -C "${CURRENT_REPO}" symbolic-ref HEAD refs/heads/unborn
  assert_runtime_failure "invalid HEAD fails closed" \
    "Breaking Change Guard: HEAD is missing or invalid."

  new_repo git-log-failure
  commit_message "feat: safe feature commit"
  wrapper_dir="${TEST_ROOT}/${AWK_BIN}-git-wrapper"
  mkdir -p "${wrapper_dir}"
  cat >"${wrapper_dir}/git" <<EOF
#!/usr/bin/env bash
if [[ \${1:-} == log ]]; then
  printf 'forced git log failure\n' >&2
  exit 42
fi
exec "${REAL_GIT}" "\$@"
EOF
  chmod +x "${wrapper_dir}/git"
  assert_runtime_failure "git log failure fails closed" \
    "Breaking Change Guard: git log failed for origin/main..HEAD." \
    main "${wrapper_dir}:${PATH}"

  new_repo shallow-history
  commit_message "feat!: older breaking commit"
  commit_message "fix: newest safe commit"
  make_shallow_clone_without_parent shallow-history
  assert_runtime_failure "shallow history fails closed" \
    "Breaking Change Guard: shallow repository detected; fetch full history before running."

  new_repo acknowledgement-exact
  commit_message "feat: safe feature commit"
  assert_guard "exact acknowledgement present" false true \
    "Before. Approved for major release. After." "Approved for major release."
  assert_guard "acknowledgement absent" false false \
    "No release approval here." "Approved for major release."
  assert_guard "partial acknowledgement is rejected" false false \
    "Approved for major" "Approved for major release."
  assert_guard "empty acknowledgement is rejected" false false "anything" ""

  new_repo breaking-acknowledgement
  commit_message "feat!: replace public API"
  assert_guard "breaking change with exact acknowledgement" true true \
    "Approved for major release." "Approved for major release."
  assert_guard "breaking change with acknowledgement capitalization mismatch" true false \
    "approved for major release." "Approved for major release."

  new_repo acknowledgement-literals
  commit_message "feat: safe acknowledgement fixture"
  multi_ack=$'Approval record:\nOwner: release team\nImpact: major version'
  assert_guard "complete multiline acknowledgement" false true \
    $'Context\nApproval record:\nOwner: release team\nImpact: major version\nEnd' "${multi_ack}"
  assert_guard "partial multiline acknowledgement is rejected" false false \
    $'Approval record:\nOwner: release team' "${multi_ack}"

  metachar_ack="Approved [v1].* \$(not-a-command); ^\$ \\ literal"
  assert_guard "acknowledgement with regex and shell metacharacters" false true \
    "prefix ${metachar_ack} suffix" "${metachar_ack}"

  large_body="Approved for major release."
  i=0
  while [[ ${i} -lt 600 ]]; do
    large_body+=$'\nfiller line that must not hide an early acknowledgement'
    i=$((i + 1))
  done
  printf 'info - large body fixture: %d bytes\n' "${#large_body}"
  assert_guard "large body with acknowledgement near start" false true \
    "${large_body}" "Approved for major release."

  new_repo exact-visible-line
  commit_message "feat: safe exact-line acknowledgement fixture"
  assert_guard "visible exact acknowledgement line" false true \
    $'Context\nApproved for major release.\nDetails' "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "leading whitespace rejects exact acknowledgement line" false false \
    " Approved for major release." "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "trailing whitespace rejects exact acknowledgement line" false false \
    "Approved for major release. " "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "case mismatch rejects exact acknowledgement line" false false \
    "approved for major release." "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "inline HTML comment rejects hidden exact acknowledgement" false false \
    "<!-- Approved for major release. -->" "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "multiline HTML comment rejects hidden exact acknowledgement" false false \
    $'<!--\nApproved for major release.\n-->' "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "same-line HTML comment closure preserves following visible lines" false true \
    $'<!-- hidden approval example -->\nApproved for major release.' \
    "Approved for major release." main "${PATH}" exact-visible-line
  assert_guard "quoted acknowledgement is not an exact visible line" false false \
    '> Approved for major release.' "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "acknowledgement configured with leading whitespace is rejected" false false \
    " Approved for major release." " Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "acknowledgement configured with trailing whitespace is rejected" false false \
    "Approved for major release. " "Approved for major release. " \
    main "${PATH}" exact-visible-line
  assert_guard "acknowledgement configured as a blockquote is rejected" false false \
    "> Approved for major release." "> Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "acknowledgement configured as an unspaced blockquote is rejected" false false \
    ">Approved for major release." ">Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "prose acknowledgement is not an exact visible line" false false \
    "Context: Approved for major release." "Approved for major release." \
    main "${PATH}" exact-visible-line
  assert_guard "CRLF exact acknowledgement line" false true \
    $'Context\r\nApproved for major release.\r\nDetails\r' \
    "Approved for major release." main "${PATH}" exact-visible-line
  assert_guard "backtick fenced code rejects hidden exact acknowledgement" false false \
    $'Context\n```text\nApproved for major release.\n```\nDetails' \
    "Approved for major release." main "${PATH}" exact-visible-line
  assert_guard "tilde fenced code rejects hidden exact acknowledgement" false false \
    $'Context\n  ~~~~markdown\nApproved for major release.\n  ~~~~~\nDetails' \
    "Approved for major release." main "${PATH}" exact-visible-line
  assert_guard "inline backtick text does not open a fence" false true \
    $'Context uses ```inline``` text.\nApproved for major release.' \
    "Approved for major release." main "${PATH}" exact-visible-line
  assert_guard "acknowledgement after a closed fence remains visible" false true \
    $'```text\nApproved for major release.\n```\nApproved for major release.' \
    "Approved for major release." main "${PATH}" exact-visible-line
  assert_guard "unclosed fence rejects hidden exact acknowledgement" false false \
    $'Context\n```text\nApproved for major release.' \
    "Approved for major release." main "${PATH}" exact-visible-line
  assert_guard "contains mode preserves substring matching" false true \
    "Before. Approved for major release. After." "Approved for major release." \
    main "${PATH}" contains
  assert_match_mode_failure "invalid acknowledgement match mode fails closed" invalid
  assert_match_mode_failure "empty acknowledgement match mode fails closed" ""
}

AWK_BIN='awk'
run_matrix

if command -v gawk >/dev/null 2>&1; then
  AWK_BIN='gawk'
  run_matrix
else
  printf 'skip - gawk matrix (gawk is not installed)\n'
fi

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
