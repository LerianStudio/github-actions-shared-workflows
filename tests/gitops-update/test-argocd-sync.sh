#!/usr/bin/env bash

# Runs the "Sync ArgoCD application" step of gitops-update.yml and the "Sync the affected
# ArgoCD applications" step of the gitops-chart-update action as written, under the runner's
# shell flags, with a stub `argocd` on PATH answering the way the real CLI does (a fatal JSON
# log line, exit 20), and asserts which failures fail the job.

set -euo pipefail

CDPATH=''
ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/gitops-update-argocd.XXXXXX")
trap 'rm -rf "${WORK_DIR}"' EXIT INT TERM
PASSED=0
FAILED=0

# extract_step <file> <step name> <out>: the step's run block, with /tmp/ moved into WORK_DIR.
extract_step() {
  awk -v step="- name: $2" '
    !found && index($0, step) && substr($0, index($0, step)) == step { found = 1; next }
    found && !inrun && /^[[:space:]]*run: \|[[:space:]]*$/ { match($0, /^ */); indent = RLENGTH; inrun = 1; next }
    inrun {
      if ($0 ~ /^[[:space:]]*$/) { print ""; next }
      match($0, /^ */)
      if (RLENGTH <= indent) exit
      print substr($0, indent + 3)
    }
  ' "$1" | sed "s#/tmp/#${WORK_DIR}/#g" >"$3"
  [[ -s $3 ]] || {
    printf 'not ok - could not extract "%s" from %s\n' "$2" "$1" >&2
    exit 1
  }
}
extract_step "${ROOT}/.github/workflows/gitops-update.yml" 'Sync ArgoCD application' "${WORK_DIR}/sync.sh"
extract_step "${ROOT}/src/deploy/gitops-chart-update/action.yml" 'Sync the affected ArgoCD applications' \
  "${WORK_DIR}/chart-sync.sh"
printf '{"changed":[{"file":"environments/benedita/helmfile/applications/dev/app/helmfile.yaml"}]}\n' \
  >"${WORK_DIR}/bump.json"

# `argocd app get` answers STUB_GET; the Nth `argocd app sync` and `argocd app wait` answer the Nth word
# of STUB_SYNCS (ok past its end) and STUB_WAITS. Each call, marked by its --prune, --operation or --health
# flag, and each `sleep` (which returns at once) lands in STUB_CALLS.
mkdir "${WORK_DIR}/bin"
cat >"${WORK_DIR}/bin/argocd" <<'STUB'
#!/usr/bin/env bash
answer() {
  case "$1" in
    ok) echo 'Health Status:      Healthy'; return 0 ;;
    busy) desc='code = FailedPrecondition desc = another operation is already in progress' ;;
    timeout) desc='timed out (600s) waiting for app "benedita-app-dev" match desired state' ;;
    unauthenticated) desc='code = Unauthenticated desc = no session information' ;;
    denied) desc='code = PermissionDenied desc = permission denied' ;;
    504) desc='code = Unknown desc = POST https://argocd.example/application.ApplicationService/Get failed with status code 504' ;;
  esac
  printf '{"level":"fatal","msg":"rpc error: %s","time":"2026-10-24T00:00:00Z"}\n' "${desc}" >&2
  return 20
}
call=$2
[[ " $* " == *" --prune "* ]] && call+=:prune
[[ " $* " == *" --operation "* ]] && call+=:operation
[[ " $* " == *" --health "* ]] && call+=:health
echo "${call}" >>"${STUB_CALLS}"
n=$(grep -c "^$2" "${STUB_CALLS}")
case "$2" in
  get) answer "${STUB_GET}" ;;
  sync) read -ra syncs <<<"${STUB_SYNCS}" && answer "${syncs[n - 1]:-ok}" ;;
  wait) read -ra waits <<<"${STUB_WAITS}" && answer "${waits[n - 1]}" ;;
esac
STUB
cat >"${WORK_DIR}/bin/sleep" <<'STUB'
#!/bin/sh
echo "sleep:$1" >>"${STUB_CALLS}"
STUB
# curl and sha256sum stand in for the chart-update step's checksum-verified download.
cat >"${WORK_DIR}/bin/curl" <<'STUB'
#!/bin/sh
cp "$(dirname "$0")/argocd" "$3"
STUB
printf '#!/bin/sh\n' >"${WORK_DIR}/bin/sha256sum"
chmod +x "${WORK_DIR}/bin/"*

# Runs the step and checks its exit status, its sync_result (synced for the chart-update step), the
# calls it made in order and the annotation it printed (a grep -E pattern). STEP (sync.sh by default),
# STUB_SYNCS and ARGOCD_PRUNE come from the caller.
assert_sync() {
  local label=$1 get=$2 waits=$3 want_status=$4 want_result=$5 want_calls=$6 want_line=$7 status=0 out result calls
  : >"${WORK_DIR}/output" && : >"${WORK_DIR}/calls"
  out=$(cd "${WORK_DIR}" && PATH="${WORK_DIR}/bin:${PATH}" STUB_GET="${get}" STUB_SYNCS="${STUB_SYNCS:-}" \
    STUB_WAITS="${waits}" STUB_CALLS="${WORK_DIR}/calls" GITHUB_OUTPUT="${WORK_DIR}/output" \
    RUNNER_TEMP="${WORK_DIR}" ARGOCD_URL=argocd.example ARGOCD_TOKEN=token APP_NAME=benedita-app-dev \
    ARGOCD_PRUNE="${ARGOCD_PRUNE:-false}" ARGOCD_SYNC_TIMEOUT=600 SYNC_TIMEOUT=600 \
    bash --noprofile --norc -eo pipefail "${WORK_DIR}/${STEP:-sync.sh}" 2>&1) || status=$?
  result=$(sed -n 's/^\(sync_result\|synced\)=//p' "${WORK_DIR}/output")
  calls=$(paste -sd ' ' "${WORK_DIR}/calls")
  if [[ ${status} -eq ${want_status} && "${result}" == "${want_result}" && "${calls}" == "${want_calls}" ]] &&
    grep -qE "${want_line}" <<<"${out}"; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${label}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (exit %s, sync_result=%s, calls=%s), printed:\n%s\n' \
      "${label}" "${status}" "${result}" "${calls}" "${out}" >&2
  fi
}

assert_sync 'an unauthenticated get fails the job with the CLI error' unauthenticated '' 1 '' 'get' \
  '^::error::.*code = Unauthenticated desc = no session information'
assert_sync 'a missing app (PermissionDenied) is still skipped with a warning' denied '' 0 failure 'get' \
  '^::warning::.*benedita-app-dev'
assert_sync 'a wait failing three times reports the CLI error, not a timeout' ok '504 504 504' 1 '' \
  'get sync wait sleep:30 wait sleep:60 wait' '^::error::.*after 3 attempts.*status code 504'
assert_sync 'a wait failing once is retried and the sync succeeds' ok '504 ok' 0 success \
  'get sync wait sleep:30 wait' '^Health Status'
STUB_SYNCS=504 assert_sync 'a refused sync is retried after 30s' ok 'ok' 0 success \
  'get sync sleep:30 sync wait' '^Sync attempt 1 failed, retrying in 30s'
STUB_SYNCS=busy ARGOCD_PRUNE=true assert_sync 'a sync refused as busy is resubmitted, prune included, once the running operation ends' \
  ok 'ok ok' 0 success 'get sync:prune wait:operation sync:prune wait' '^Health Status'
STUB_SYNCS=busy assert_sync 'an operation still running after the sync timeout fails the job with the CLI error' ok 'timeout' 1 '' \
  'get sync wait:operation' '^::error::An Argo CD operation was still running on benedita-app-dev after 600s: .*timed out \(600s\)'
STUB_SYNCS=busy assert_sync 'an API error while waiting on the running operation gets the 30s retry' ok '504 ok' 0 success \
  'get sync wait:operation sleep:30 sync wait' '^Sync attempt 1 failed, retrying in 30s'
STUB_SYNCS='busy busy busy busy busy' assert_sync 'an app busy on every attempt fails after 5 sync attempts' ok 'ok ok ok ok' 1 '' \
  'get sync wait:operation sync wait:operation sync wait:operation sync wait:operation sync' \
  '^::error::.*after 5 attempts.*another operation is already in progress'
STEP=chart-sync.sh STUB_SYNCS=busy assert_sync 'chart update: a sync refused as busy is resubmitted once the running operation ends' \
  '' 'ok ok' 0 true 'sync wait:operation sync wait:health' '^::notice::benedita-app-dev is healthy'
STEP=chart-sync.sh STUB_SYNCS=busy assert_sync 'chart update: an operation still running after the sync timeout fails the leg' \
  '' 'timeout' 1 false 'sync wait:operation' '^::error::benedita-app-dev did not reach a healthy state'

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
