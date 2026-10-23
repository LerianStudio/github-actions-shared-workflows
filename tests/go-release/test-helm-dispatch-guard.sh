#!/usr/bin/env bash

# Runs the helm_dispatch_guard step from go-release.yml as written: an extra_builds
# group dispatching the top-level chart is warned about by index, a group for a
# different chart or with no dispatch of its own is not, and the step never fails.

set -euo pipefail

CDPATH=''
RELEASE_WORKFLOW="$(cd -- "$(dirname -- "$0")/../.." && pwd)/.github/workflows/go-release.yml"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/go-release-helm-guard.XXXXXX")
PASSED=0
FAILED=0
trap 'rm -rf "${WORK_DIR}"' EXIT

# Prints the dedented `run: |` body of the first step with the given name.
extract_step() {
  awk -v want="$1" '
    $0 ~ "^[[:space:]]*- name: " want "$" { found = 1; next }
    found && !inrun && /^[[:space:]]*run: \|[[:space:]]*$/ { match($0, /^ */); indent = RLENGTH; inrun = 1; next }
    inrun {
      if ($0 ~ /^[[:space:]]*$/) { print ""; next }
      match($0, /^ */)
      if (RLENGTH <= indent) exit
      print substr($0, indent + 3)
    }
  ' "${RELEASE_WORKFLOW}"
}

extract_step 'Flag extra_builds groups dispatching the top-level chart' >"${WORK_DIR}/guard.sh"
[[ -s "${WORK_DIR}/guard.sh" ]] || {
  printf 'not ok - could not extract the helm_dispatch_guard step from %s\n' "${RELEASE_WORKFLOW}" >&2
  exit 1
}

# Runs the step and compares the warning titles it printed with the expected ones.
# The step must exit 0 in every case, and every line it prints must be a whole
# warning command ending in the remediation, so none is cut short by a newline.
assert_warnings() {
  local label=$1 extra_builds=$2 expected=$3 status=0 out got stray
  out=$(EXTRA_BUILDS="${extra_builds}" HELM_CHART=my-chart DRY_RUN=false bash "${WORK_DIR}/guard.sh" 2>&1) || status=$?
  got=$(sed -n 's/^::warning title=\([^:]*\)::.*/\1/p' <<<"${out}")
  stray=$(grep -v '^::warning title=.*top-level helm_values_key_mappings\.$' <<<"${out}" | grep -v '^$' || true)
  if [[ ${status} -eq 0 && "${got}" == "${expected}" && -z "${stray}" ]]; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${label}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (exit %s), printed:\n%s\n' "${label}" "${status}" "${out}" >&2
  fi
}

WORKER='"filter_paths": "cmd/worker", "app_name_overrides": "cmd/worker:my-app-worker"'
MIGRATIONS='"filter_paths": "migrations-image", "app_name_overrides": "migrations-image:my-app-migrations"'

assert_warnings 'same chart as the top level: the group is named' \
  "[{${WORKER}}, {${MIGRATIONS}, \"enable_helm_dispatch\": true, \"helm_chart\": \"my-chart\", \"helm_values_key_mappings\": \"{}\"}]" \
  'extra_builds[1] dispatches the top-level chart'

assert_warnings 'newline-separated filter_paths stay on the one warning line' \
  '[{"filter_paths": "cmd/worker\ncmd/scheduler", "enable_helm_dispatch": true, "helm_chart": "my-chart"}]' \
  'extra_builds[0] dispatches the top-level chart'

assert_warnings 'group dispatch with no chart of its own falls on the top-level chart' \
  "[{${WORKER}, \"enable_helm_dispatch\": true}]" \
  'extra_builds[0] dispatches the top-level chart'

assert_warnings 'a group dispatching a different chart is left alone' \
  "[{${WORKER}, \"enable_helm_dispatch\": true, \"helm_chart\": \"other-chart\"}]" \
  ''

assert_warnings 'the central shape from the docs is left alone' \
  "[{${WORKER}}, {${MIGRATIONS}}]" \
  ''

assert_warnings 'an unparsable value is left to extra_build to report' \
  '[{"filter_paths": ' \
  ''

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
