#!/usr/bin/env bash

# Runs the "Sync ArgoCD application" step of gitops-update.yml as written, under the
# runner's shell flags, with a stub `argocd` on PATH answering the way the real CLI
# does (a fatal JSON log line, exit 20), and asserts which failures fail the job.

set -euo pipefail

CDPATH=''
WORKFLOW="$(cd -- "$(dirname -- "$0")/../.." && pwd)/.github/workflows/gitops-update.yml"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/gitops-update-argocd.XXXXXX")
trap 'rm -rf "${WORK_DIR}"' EXIT INT TERM
PASSED=0
FAILED=0

awk '
  $0 ~ /^[[:space:]]*- name: Sync ArgoCD application$/ { found = 1; next }
  found && !inrun && /^[[:space:]]*run: \|[[:space:]]*$/ { match($0, /^ */); indent = RLENGTH; inrun = 1; next }
  inrun {
    if ($0 ~ /^[[:space:]]*$/) { print ""; next }
    match($0, /^ */)
    if (RLENGTH <= indent) exit
    print substr($0, indent + 3)
  }
' "${WORKFLOW}" >"${WORK_DIR}/sync.sh"
[[ -s ${WORK_DIR}/sync.sh ]] || {
  printf 'not ok - could not extract the sync step from %s\n' "${WORKFLOW}" >&2
  exit 1
}

# `argocd app get --refresh` answers STUB_GET; each `argocd app wait` answers the next word of
# STUB_WAITS; every `argocd app sync` answers STUB_SYNC (ok). `sleep` returns at once.
mkdir "${WORK_DIR}/bin"
cat >"${WORK_DIR}/bin/argocd" <<'STUB'
#!/usr/bin/env bash
answer() {
  case "$1" in
    ok) printf 'Sync Policy:        Automated (Prune)\nHealth Status:      Healthy\n'; return 0 ;;
    manual) echo 'Sync Policy:        Manual'; return 0 ;;
    busy) desc='code = FailedPrecondition desc = another operation is already in progress' ;;
    unauthenticated) desc='code = Unauthenticated desc = no session information' ;;
    denied) desc='code = PermissionDenied desc = permission denied' ;;
    504) desc='code = Unknown desc = POST https://argocd.example/application.ApplicationService/Get failed with status code 504' ;;
  esac
  printf '{"level":"fatal","msg":"rpc error: %s","time":"2026-10-24T00:00:00Z"}\n' "${desc}" >&2
  return 20
}
case "$2" in
  # Without --refresh the server reads the branch head from a cache that can predate the push.
  get) [[ " $* " == *" --refresh "* ]] || exit 2; answer "${STUB_GET}" ;;
  sync) answer "${STUB_SYNC:-ok}" ;;
  wait)
    echo x >>"${STUB_WAIT_LOG}"
    read -ra waits <<<"${STUB_WAITS}"
    answer "${waits[$(($(wc -l <"${STUB_WAIT_LOG}") - 1))]}"
    ;;
esac
STUB
printf '#!/bin/sh\n' >"${WORK_DIR}/bin/sleep"
chmod +x "${WORK_DIR}/bin/argocd" "${WORK_DIR}/bin/sleep"

# Runs the step and checks its exit status, its sync_result, the number of waits
# and the annotation it printed (a grep -E pattern).
assert_sync() {
  local label=$1 get=$2 waits=$3 want_status=$4 want_result=$5 want_waits=$6 want_line=$7 status=0 out result got_waits
  : >"${WORK_DIR}/output" && : >"${WORK_DIR}/waits"
  out=$(PATH="${WORK_DIR}/bin:${PATH}" STUB_GET="${get}" STUB_WAITS="${waits}" STUB_WAIT_LOG="${WORK_DIR}/waits" \
    GITHUB_OUTPUT="${WORK_DIR}/output" RUNNER_TEMP="${WORK_DIR}" ARGOCD_URL=argocd.example ARGOCD_TOKEN='' \
    APP_NAME=benedita-app-dev ARGOCD_PRUNE=false ARGOCD_SYNC_TIMEOUT=600 \
    bash --noprofile --norc -eo pipefail "${WORK_DIR}/sync.sh" 2>&1) || status=$?
  result=$(sed -n 's/^sync_result=//p' "${WORK_DIR}/output")
  got_waits=$(wc -l <"${WORK_DIR}/waits")
  if [[ ${status} -eq ${want_status} && "${result}" == "${want_result}" && ${got_waits} -eq ${want_waits} ]] &&
    grep -qE "${want_line}" <<<"${out}"; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${label}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (exit %s, sync_result=%s, waits=%s), printed:\n%s\n' \
      "${label}" "${status}" "${result}" "${got_waits}" "${out}" >&2
  fi
}

assert_sync 'an unauthenticated get fails the job with the CLI error' unauthenticated '' 1 '' 0 \
  '^::error::.*code = Unauthenticated desc = no session information'
assert_sync 'a missing app (PermissionDenied) is still skipped with a warning' denied '' 0 failure 0 \
  '^::warning::.*benedita-app-dev'
assert_sync 'a wait failing three times reports the CLI error, not a timeout' ok '504 504 504' 1 '' 3 \
  '^::error::.*after 3 attempts.*status code 504'
assert_sync 'a wait failing once is retried and the sync succeeds' ok '504 ok' 0 success 2 \
  '^Health Status'
STUB_SYNC=busy assert_sync 'an automated app Argo CD is already syncing is waited on' ok 'ok' 0 success 1 \
  '^Argo CD is already syncing benedita-app-dev under its automated policy'
STUB_SYNC=busy assert_sync 'a manual app held by another operation fails after 5 sync attempts' manual '' 1 '' 0 \
  '^::error::.*after 5 attempts.*another operation is already in progress'

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
