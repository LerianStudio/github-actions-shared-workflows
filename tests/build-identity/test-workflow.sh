#!/usr/bin/env bash

# Tests the two inline shell blocks in .github/workflows/build.yml that decide what
# the verification is handed: the version the image is published under, and whether
# the app's Dockerfile adopted the contract at all. Then asserts the step wiring
# around them that makes the verification a pre-push gate.
#
# Both blocks are extracted from build.yml and executed as written, so a change to
# the workflow is what this asserts against — not a copy of it. No docker, no go.

set -euo pipefail

CDPATH=''
# shellcheck source=tests/build-identity/lib.sh
source "$(dirname -- "$0")/lib.sh"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/build-identity-workflow.XXXXXX")
PASSED=0
FAILED=0

cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT INT TERM

[[ -f ${WORKFLOW} ]] || {
  printf 'not ok - workflow is missing: %s\n' "${WORKFLOW}" >&2
  exit 1
}

record_pass() {
  PASSED=$((PASSED + 1))
  printf 'ok - %s\n' "$1"
}

record_fail() {
  FAILED=$((FAILED + 1))
  printf 'not ok - %s: %s\n' "$1" "$2" >&2
}

for step in version identity; do
  extract_run_block "${step}" >"${WORK_DIR}/${step}.sh"
  if [[ ! -s "${WORK_DIR}/${step}.sh" ]]; then
    printf 'not ok - could not extract the run block of step %s from %s\n' \
      "${step}" "${WORKFLOW}" >&2
    exit 1
  fi
done

# Runs the version step and asserts the `version=` it writes to GITHUB_OUTPUT.
assert_version() {
  local label=$1 release_version=$2 github_ref=$3 expected=$4
  local out="${WORK_DIR}/output"
  local status resolved

  : >"${out}"
  if RELEASE_VERSION="${release_version}" GITHUB_REF="${github_ref}" \
    GITHUB_OUTPUT="${out}" bash "${WORK_DIR}/version.sh" >/dev/null 2>&1; then
    status=0
  else
    status=$?
  fi

  if [[ ${expected} == 'rejected' ]]; then
    if [[ ${status} -eq 0 ]]; then
      record_fail "${label}" 'expected a non-zero exit, got 0'
    else
      record_pass "${label}"
    fi
    return
  fi

  resolved=$(sed -n 's/^version=//p' "${out}")
  if [[ ${status} -ne 0 ]]; then
    record_fail "${label}" "expected exit 0, got ${status}"
  elif [[ ${resolved} != "${expected}" ]]; then
    record_fail "${label}" "expected version [${expected}], got [${resolved}]"
  else
    record_pass "${label}"
  fi
}

# Runs the adoption gate against a Dockerfile snippet and asserts `adopted=`, plus
# the annotation it prints: a non-adopting image gets a ::warning:: naming it and
# pointing at the contract doc, an adopting one gets no warning at all. The optional
# fourth argument is require_build_identity as the runner hands it (`true`/`false`);
# with it set, a non-adopting Dockerfile is expected to fail: expected=`error`
# asserts a non-zero exit, an ::error:: naming the input and the doc, no ::warning::.
assert_adopted() {
  local label=$1 dockerfile_body=$2 expected=$3 required=${4:-}
  local out="${WORK_DIR}/output"
  local dockerfile="${WORK_DIR}/Dockerfile"
  local adopted stdout warnings errors status

  : >"${out}"
  printf '%s\n' "${dockerfile_body}" >"${dockerfile}"
  if stdout=$(APP_NAME=test-app DOCKERFILE="${dockerfile}" GITHUB_OUTPUT="${out}" \
    REQUIRE_BUILD_IDENTITY="${required}" bash "${WORK_DIR}/identity.sh" 2>/dev/null); then
    status=0
  else
    status=$?
  fi

  warnings=$(grep -E '^::warning::' <<<"${stdout}" || true)
  if [[ ${expected} == 'error' ]]; then
    errors=$(grep -E '^::error::' <<<"${stdout}" || true)
    if [[ ${status} -eq 0 ]]; then
      record_fail "${label}" 'expected a non-zero exit, got 0'
    elif [[ -n ${warnings} ]]; then
      record_fail "${label}" "expected no ::warning::, got [${warnings}]"
    elif ! grep -E 'require_build_identity' <<<"${errors}" | grep -qE 'docs/build\.md'; then
      record_fail "${label}" "expected an ::error:: naming require_build_identity and docs/build.md, got [${stdout}]"
    else
      record_pass "${label}"
    fi
    return
  fi
  if [[ ${status} -ne 0 ]]; then
    record_fail "${label}" 'the adoption gate exited non-zero'
    return
  fi

  adopted=$(sed -n 's/^adopted=//p' "${out}")
  if [[ ${adopted} != "${expected}" ]]; then
    record_fail "${label}" "expected adopted=[${expected}], got [${adopted}]"
  elif [[ ${expected} == 'true' && -n ${warnings} ]]; then
    record_fail "${label}" "expected no ::warning::, got [${warnings}]"
  elif [[ ${expected} == 'false' ]] && ! grep -E 'test-app' <<<"${warnings}" |
    grep -E 'published without compiled build identity' |
    grep -qE 'docs/build\.md'; then
    record_fail "${label}" "expected a ::warning:: naming test-app and docs/build.md, got [${stdout}]"
  else
    record_pass "${label}"
  fi
}

assert_version 'semantic-release version passes through' '1.2.3' 'refs/heads/main' '1.2.3'
assert_version 'tag loses its leading v' '' 'refs/tags/v1.2.3' '1.2.3'
assert_version 'prefixed rc tag resolves' '' 'refs/tags/agent-v1.0.0-rc.2' '1.0.0-rc.2'
assert_version 'multi-dash prefixed beta tag resolves' '' \
  'refs/tags/control-plane-v1.0.0-beta.1' '1.0.0-beta.1'
assert_version 'non-semver tag is rejected' '' 'refs/tags/nightly' 'rejected'
assert_version 'branch ref is rejected' '' 'refs/heads/develop' 'rejected'
assert_version 'chart tag without v is rejected' '' 'refs/tags/helm-chart-0.1.0' 'rejected'
# Build metadata is rejected deliberately: a Docker tag cannot contain '+', so a
# version carrying it could never be published as the image tag anyway. Failing on
# the version is louder than failing later on an invalid reference.
assert_version 'build metadata is rejected' '' 'refs/tags/v1.2.3+build.5' 'rejected'

assert_adopted 'bare ARG REVISION adopts' 'FROM scratch
ARG REVISION' 'true'
assert_adopted 'ARG REVISION with a default adopts' 'FROM scratch
ARG REVISION=unknown' 'true'
assert_adopted 'lowercase arg adopts' 'FROM scratch
arg REVISION' 'true'
assert_adopted 'indented ARG REVISION adopts' 'FROM scratch
  ARG REVISION' 'true'
assert_adopted 'ARG REVISION=abc adopts' 'FROM scratch
ARG REVISION=abc' 'true'
assert_adopted 'padded ARG REVISION adopts' 'FROM scratch
  ARG   REVISION   ' 'true'
# Build-arg names are case-sensitive: these never receive REVISION=<sha>.
assert_adopted 'lowercase arg name does not adopt' 'FROM scratch
ARG revision' 'false'
assert_adopted 'capitalised arg name does not adopt' 'FROM scratch
ARG Revision' 'false'
assert_adopted 'ARG REVISION_ID does not adopt' 'FROM scratch
ARG REVISION_ID=abc' 'false'
assert_adopted 'ARG REVISIONS does not adopt' 'FROM scratch
ARG REVISIONS' 'false'
assert_adopted 'commented ARG REVISION does not adopt' 'FROM scratch
# ARG REVISION' 'false'
assert_adopted 'no ARG at all does not adopt' 'FROM scratch' 'false'
# require_build_identity turns the not-adopted warning into a failure, and only that.
assert_adopted 'required + ARG REVISION adopts without a warning' 'FROM scratch
ARG REVISION' 'true' 'true'
assert_adopted 'required + no ARG REVISION fails the build' 'FROM scratch' 'error' 'true'
assert_adopted 'required + ARG REVISION_ID fails the build' 'FROM scratch
ARG REVISION_ID=abc' 'error' 'true'
assert_adopted 'not required + no ARG REVISION only warns' 'FROM scratch' 'false' 'false'

# --- Wiring: what makes the verification a pre-push gate -------------------------
# The blocks above are only half the contract; the other half is the YAML around
# them. These assertions read build.yml as text so reordering the steps, pushing the
# verification build, or feeding verify different values than the published build
# goes red here instead of shipping an image the gate never looked at.

# Prints the line number of the step with the given name; empty if absent or duplicated.
step_line() {
  local lines
  lines=$(grep -nE "^[[:space:]]*- name: $1[[:space:]]*$" "${WORKFLOW}" | cut -d: -f1)
  [[ $(wc -l <<<"${lines}") -eq 1 ]] && printf '%s' "${lines}"
}

# Prints the step's YAML, from its `- name:` line up to the next step or dedent.
step_block() {
  awk -v want="$1" '
    !found && $0 ~ "^[[:space:]]*- name: " want "[[:space:]]*$" {
      match($0, /^ */); indent = RLENGTH; found = 1; print; next
    }
    found {
      if ($0 ~ /^[[:space:]]*$/) next
      match($0, /^ */)
      if (RLENGTH <= indent) exit
      print
    }
  ' "${WORKFLOW}"
}

# Prints the value of a `key: value` line inside a step block (first match).
block_value() {
  sed -n "s/^[[:space:]]*$2: //p" <<<"$1" | head -n 1
}

assert_wiring() {
  local label=$1 detail=$2
  shift 2
  if "$@"; then record_pass "${label}"; else record_fail "${label}" "${detail}"; fi
}

DETECT_NAME='Detect build identity contract'
VERIFY_BUILD_NAME='Build image for verification'
VERIFY_NAME='Verify build identity'
PUSH_NAME='Build and push Docker image'
VERIFY_BUILD_LINE=$(step_line "${VERIFY_BUILD_NAME}" || true)
VERIFY_LINE=$(step_line "${VERIFY_NAME}" || true)
PUSH_LINE=$(step_line "${PUSH_NAME}" || true)
DETECT_BLOCK=$(step_block "${DETECT_NAME}")
VERIFY_BUILD_BLOCK=$(step_block "${VERIFY_BUILD_NAME}")
VERIFY_BLOCK=$(step_block "${VERIFY_NAME}")
PUSH_BLOCK=$(step_block "${PUSH_NAME}")
EXPECTED_VERSION_EXPR=$(block_value "${VERIFY_BLOCK}" EXPECTED_VERSION)
EXPECTED_REVISION_EXPR=$(block_value "${VERIFY_BLOCK}" EXPECTED_REVISION)

steps_in_order() {
  [[ -n ${VERIFY_BUILD_LINE} && -n ${VERIFY_LINE} && -n ${PUSH_LINE} ]] &&
    ((VERIFY_BUILD_LINE < VERIFY_LINE && VERIFY_LINE < PUSH_LINE))
}
block_has_line() {
  grep -qxE "[[:space:]]*$2" <<<"$1"
}
verification_build_is_local() {
  block_has_line "${VERIFY_BUILD_BLOCK}" 'push: false' &&
    block_has_line "${VERIFY_BUILD_BLOCK}" 'load: true'
}
# The literals are GitHub expressions, not shell ones: single quotes are the point.
# shellcheck disable=SC2016
verify_reads_computed_values() {
  [[ ${EXPECTED_VERSION_EXPR} == '${{ steps.version.outputs.version }}' &&
    ${EXPECTED_REVISION_EXPR} == '${{ steps.source.outputs.sha }}' ]]
}
build_args_match() {
  local args
  args=$(awk '{ sub(/^[[:space:]]+/, "") } 1' <<<"$1")
  grep -qxF "VERSION=${EXPECTED_VERSION_EXPR}" <<<"${args}" &&
    grep -qxF "REVISION=${EXPECTED_REVISION_EXPR}" <<<"${args}"
}
verify_inspects_verification_image() {
  local image
  image=$(block_value "${VERIFY_BLOCK}" IMAGE)
  [[ -n ${image} && ${image} == "$(block_value "${VERIFY_BUILD_BLOCK}" tags)" ]]
}
# shellcheck disable=SC2016
gate_reads_require_input() {
  [[ $(block_value "${DETECT_BLOCK}" REQUIRE_BUILD_IDENTITY) == '${{ inputs.require_build_identity }}' ]]
}
verify_gated_on_adoption() {
  grep -qxE "[[:space:]]*if: (steps\.preflight\.outputs\.should_build != 'false' && )?steps\.identity\.outputs\.adopted == 'true'" <<<"${VERIFY_BLOCK}"
}

assert_wiring 'verify runs after the verification build and before the push' \
  "lines: verification build=${VERIFY_BUILD_LINE:-missing}, verify=${VERIFY_LINE:-missing}, push=${PUSH_LINE:-missing}" \
  steps_in_order
assert_wiring 'verification build is loaded locally, never pushed' \
  "expected push: false and load: true in step ${VERIFY_BUILD_NAME}" \
  verification_build_is_local
assert_wiring 'verify expects the computed version and source revision' \
  "got EXPECTED_VERSION=[${EXPECTED_VERSION_EXPR}] EXPECTED_REVISION=[${EXPECTED_REVISION_EXPR}]" \
  verify_reads_computed_values
assert_wiring 'verification build receives the values verify expects' \
  "VERSION=/REVISION= build-args of ${VERIFY_BUILD_NAME} differ from verify's env" \
  build_args_match "${VERIFY_BUILD_BLOCK}"
assert_wiring 'published build receives the values verify expects' \
  "VERSION=/REVISION= build-args of ${PUSH_NAME} differ from verify's env" \
  build_args_match "${PUSH_BLOCK}"
assert_wiring 'verify inspects the image the verification build tagged' \
  "IMAGE in ${VERIFY_NAME} differs from tags in ${VERIFY_BUILD_NAME}" \
  verify_inspects_verification_image
assert_wiring 'verify runs only when the Dockerfile adopted the contract' \
  "expected if: ... steps.identity.outputs.adopted == 'true' in ${VERIFY_NAME}" \
  verify_gated_on_adoption
assert_wiring 'adoption gate reads the require_build_identity input' \
  "expected REQUIRE_BUILD_IDENTITY: \${{ inputs.require_build_identity }} in ${DETECT_NAME}" \
  gate_reads_require_input

# An extra_builds group may opt out (or in) on its own; omitted, it inherits the
# top-level input. Loose equality coerces null and false both to 0, so the
# inherit case must be detected with toJSON(...) == 'null', not with == null.
RELEASE_WORKFLOW="$(dirname -- "${WORKFLOW}")/go-release.yml"
# shellcheck disable=SC2016
extra_build_group_overrides_require_input() {
  grep -qxF "      require_build_identity: \${{ matrix.group.require_build_identity == true || (toJSON(matrix.group.require_build_identity) == 'null' && inputs.require_build_identity == true) }}" "${RELEASE_WORKFLOW}"
}
assert_wiring 'extra_builds group require_build_identity overrides the top-level input' \
  "expected the per-group null-fallback expression in ${RELEASE_WORKFLOW}" \
  extra_build_group_overrides_require_input

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
