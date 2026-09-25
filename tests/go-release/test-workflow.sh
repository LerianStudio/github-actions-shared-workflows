#!/usr/bin/env bash

# Asserts the per-group boolean overrides that go-release.yml forwards to build.yml
# for each extra_builds group: an explicit true/false on the group wins, an omitted
# key inherits (or defaults). Expression loose equality coerces null and false both
# to 0, so `matrix.group.x == null` is also true for an explicit false; the inherit
# case must be detected with toJSON(...) == 'null'.

set -euo pipefail

CDPATH=''
RELEASE_WORKFLOW="$(cd -- "$(dirname -- "$0")/../.." && pwd)/.github/workflows/go-release.yml"
PASSED=0
FAILED=0

[[ -f ${RELEASE_WORKFLOW} ]] || {
  printf 'not ok - workflow is missing: %s\n' "${RELEASE_WORKFLOW}" >&2
  exit 1
}

# Asserts that go-release.yml carries the given line verbatim.
assert_line() {
  local label=$1 line=$2
  if grep -qxF "${line}" "${RELEASE_WORKFLOW}"; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${label}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s: expected line [%s] in %s\n' "${label}" "${line}" "${RELEASE_WORKFLOW}" >&2
  fi
}

# Top-level input fallback: explicit group value wins, omitted inherits the input.
for key in enable_dockerhub enable_ghcr require_build_identity; do
  assert_line "extra_builds group ${key} honors an explicit false and inherits when omitted" \
    "      ${key}: \${{ matrix.group.${key} == true || (toJSON(matrix.group.${key}) == 'null' && inputs.${key} == true) }}"
done

# No input fallback: explicit group value wins, omitted defaults to true.
assert_line 'extra_builds group enable_gitops_artifacts honors an explicit false and defaults to true' \
  "      enable_gitops_artifacts: \${{ matrix.group.enable_gitops_artifacts == true || toJSON(matrix.group.enable_gitops_artifacts) == 'null' }}"

if grep -nE 'matrix\.group\.[a-z_]+ *[!=]= *null' "${RELEASE_WORKFLOW}" >&2; then
  FAILED=$((FAILED + 1))
  printf 'not ok - no per-group comparison against null (coerces an explicit false): see lines above\n' >&2
else
  PASSED=$((PASSED + 1))
  printf 'ok - no per-group comparison against null\n'
fi

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
