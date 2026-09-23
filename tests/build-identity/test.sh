#!/usr/bin/env bash

# Tests the `Verify build identity` step of .github/workflows/build.yml. The step's
# run block is extracted from the workflow and executed as written, against throwaway
# scratch images that imitate (or break) the --version contract of docs/build.md.
#
# Requires docker and go on the host. No network: the fixtures have no dependencies
# and nothing is pulled or pushed. `docker` is shimmed on PATH so every `docker run`
# the step issues must carry --pull=never and --network none, or the shim refuses it.

set -euo pipefail

CDPATH=''
# shellcheck source=tests/build-identity/lib.sh
source "$(dirname -- "$0")/lib.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/build-identity.XXXXXX")
VERIFIER="${TEST_ROOT}/verify.sh"
SHIM_DIR="${TEST_ROOT}/bin"
IMAGE_PREFIX="build-identity-test-$$"
GOOD_IMAGE="${IMAGE_PREFIX}/good:test"
SILENT_IMAGE="${IMAGE_PREFIX}/silent:test"
UNSTAMPED_IMAGE="${IMAGE_PREFIX}/unstamped:test"
HALF_IMAGE="${IMAGE_PREFIX}/half:test"
SLOW_IMAGE="${IMAGE_PREFIX}/slow:test"
STUBBORN_IMAGE="${IMAGE_PREFIX}/stubborn:test"
INJECT_IMAGE="${IMAGE_PREFIX}/inject:test"
BADVERSION_IMAGE="${IMAGE_PREFIX}/badversion:test"
BADSERVICE_IMAGE="${IMAGE_PREFIX}/badservice:test"
MISSING_IMAGE="${IMAGE_PREFIX}/missing:test"
ALL_IMAGES=("${GOOD_IMAGE}" "${SILENT_IMAGE}" "${UNSTAMPED_IMAGE}" "${HALF_IMAGE}"
  "${SLOW_IMAGE}" "${STUBBORN_IMAGE}" "${INJECT_IMAGE}" "${BADVERSION_IMAGE}" "${BADSERVICE_IMAGE}")
BUILT_VERSION='4.0.3'
BUILT_REVISION='0123456789abcdef0123456789abcdef01234567'
# The step names its container after GITHUB_RUN_ID; a per-run value keeps cleanup and
# the leftover check away from containers of any other run on this host.
RUN_ID="test$$"
CONTAINER_FILTER="name=build-identity-verify-${RUN_ID}-"
PASSED=0
FAILED=0

cleanup() {
  local ids
  ids=$(docker ps -aq --filter "${CONTAINER_FILTER}" 2>/dev/null || true)
  # shellcheck disable=SC2086 # one container id per word
  [[ -z ${ids} ]] || docker rm -f ${ids} >/dev/null 2>&1 || true
  docker rmi -f "${ALL_IMAGES[@]}" >/dev/null 2>&1 || true
  rm -rf "${TEST_ROOT}"
}
trap cleanup EXIT INT TERM

for tool in docker go jq; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    printf 'not ok - %s is required to run this test\n' "${tool}" >&2
    exit 1
  fi
done

extract_run_block verify >"${VERIFIER}"
if [[ ! -s ${VERIFIER} ]]; then
  printf 'not ok - could not extract the run block of step verify from %s\n' \
    "${WORKFLOW}" >&2
  exit 1
fi

# The shim delegates to the real docker, refusing any `run` without the two flags.
REAL_DOCKER=$(command -v docker)
mkdir -p "${SHIM_DIR}"
cat >"${SHIM_DIR}/docker" <<SHIM
#!/usr/bin/env bash
if [[ \${1:-} == run ]]; then
  [[ " \$* " == *" --pull=never "* ]] || { echo 'shim: docker run without --pull=never' >&2; exit 97; }
  [[ " \$* " == *" --network none "* ]] || { echo 'shim: docker run without --network none' >&2; exit 97; }
fi
exec "${REAL_DOCKER}" "\$@"
SHIM
chmod +x "${SHIM_DIR}/docker"

record_pass() {
  PASSED=$((PASSED + 1))
  printf 'ok - %s\n' "$1"
}

record_fail() {
  FAILED=$((FAILED + 1))
  printf 'not ok - %s: %s\n' "$1" "$2" >&2
}

# Builds a scratch image whose entrypoint is the fixture binary.
build_fixture() {
  local name=$1 source=$2 image=$3 ldflags=$4
  local dir="${TEST_ROOT}/${name}"

  mkdir -p "${dir}"
  printf '%s\n' "${source}" >"${dir}/main.go"
  printf 'module buildidentityfixture\n\ngo 1.22\n' >"${dir}/go.mod"
  (
    cd "${dir}" || exit 99
    CGO_ENABLED=0 GOPROXY=off GOFLAGS=-mod=mod \
      timeout 120 go build -trimpath -ldflags "${ldflags}" -o fixture ./...
  )
  printf 'FROM scratch\nCOPY fixture /fixture\nENTRYPOINT ["/fixture"]\n' \
    >"${dir}/Dockerfile"
  timeout 180 docker build -q -t "${image}" "${dir}" >/dev/null
}

# A binary that answers --version with a fixed, possibly hostile, line of output.
raw_source() {
  # shellcheck disable=SC2016 # the backticks are a Go raw string, not a command
  printf 'package main\n\nimport "os"\n\nfunc main() {\n\tos.Stdout.WriteString(`%s` + "\\n")\n}\n' "$1"
}

# Runs the step and asserts the exit status, a fragment its output must contain and,
# optionally, a fragment it must never contain.
assert_verify() {
  local label=$1 expected_status=$2 expected_fragment=$3
  local image=$4 expected_version=$5 expected_revision=$6 run_timeout=${7:-30}
  local forbidden=${8:-}
  local output_file="${TEST_ROOT}/output"
  local status

  if PATH="${SHIM_DIR}:${PATH}" GITHUB_RUN_ID="${RUN_ID}" RUN_TIMEOUT="${run_timeout}" IMAGE="${image}" \
    EXPECTED_VERSION="${expected_version}" EXPECTED_REVISION="${expected_revision}" \
    bash "${VERIFIER}" >"${output_file}" 2>&1; then
    status=0
  else
    status=$?
  fi

  if [[ ${status} -ne ${expected_status} ]]; then
    record_fail "${label}" \
      "expected exit ${expected_status}, got ${status}: $(<"${output_file}")"
  elif ! grep -qF -- "${expected_fragment}" "${output_file}"; then
    record_fail "${label}" \
      "expected output to contain [${expected_fragment}], got [$(<"${output_file}")]"
  elif [[ -n ${forbidden} ]] && grep -qF -- "${forbidden}" "${output_file}"; then
    record_fail "${label}" \
      "output must not contain [${forbidden}], got [$(<"${output_file}")]"
  else
    record_pass "${label}"
  fi
}

# Imitates the identity JSON of docs/build.md, built from -X main.*.
GOOD_SOURCE='package main

import (
	"encoding/json"
	"os"
)

var version, revision string

func main() {
	if len(os.Args) > 1 && os.Args[1] == "--version" {
		_ = json.NewEncoder(os.Stdout).Encode(map[string]interface{}{
			"schemaVersion": "v1",
			"service":       "fixture-api",
			"version":       version,
			"revision":      revision,
			"buildTime":     "2026-09-23T00:00:00Z",
			"modified":      false,
			"goVersion":     "go1.26.6",
		})
		return
	}
	os.Exit(1)
}'

# A binary that never adopted the contract: it ignores --version and logs instead.
SILENT_SOURCE='package main

import "fmt"

func main() {
	fmt.Println("level=info msg=\"starting service\"")
}'

# Never answers in time, but exits on SIGTERM like any Go binary.
SLOW_SOURCE='package main

import "time"

func main() {
	time.Sleep(20 * time.Second)
}'

# Never answers and ignores SIGTERM, as a server that shuts down slowly would: the
# docker client forwards timeout's SIGTERM and would wait out the full sleep.
STUBBORN_SOURCE='package main

import (
	"os/signal"
	"syscall"
	"time"
)

func main() {
	signal.Ignore(syscall.SIGTERM)
	time.Sleep(120 * time.Second)
}'

IDENTITY_FIELDS="\"version\":\"${BUILT_VERSION}\",\"revision\":\"${BUILT_REVISION}\""

printf 'info - building fixtures (go build + docker build)\n'
build_fixture good "${GOOD_SOURCE}" "${GOOD_IMAGE}" \
  "-s -w -X main.version=${BUILT_VERSION} -X main.revision=${BUILT_REVISION}"
build_fixture silent "${SILENT_SOURCE}" "${SILENT_IMAGE}" "-s -w"
# Half-adoption: ARG REVISION turns verification on, but nothing reaches the linker.
build_fixture unstamped "${GOOD_SOURCE}" "${UNSTAMPED_IMAGE}" "-s -w"
build_fixture half "${GOOD_SOURCE}" "${HALF_IMAGE}" \
  "-s -w -X main.version=${BUILT_VERSION}"
build_fixture slow "${SLOW_SOURCE}" "${SLOW_IMAGE}" "-s -w"
build_fixture stubborn "${STUBBORN_SOURCE}" "${STUBBORN_IMAGE}" "-s -w"
# A goVersion that, printed raw, would start a new line with a workflow command.
build_fixture inject "$(raw_source "{${IDENTITY_FIELDS},\"goVersion\":\"go1.26\\n::error::INJECTED\"}")" \
  "${INJECT_IMAGE}" "-s -w"
build_fixture badversion "$(raw_source '{"version":"4.0.3 && id","revision":"x"}')" \
  "${BADVERSION_IMAGE}" "-s -w"
build_fixture badservice "$(raw_source "{${IDENTITY_FIELDS},\"service\":\"svc+evil\"}")" \
  "${BADSERVICE_IMAGE}" "-s -w"

assert_verify "matching identity passes" 0 \
  "::notice::build identity: ${GOOD_IMAGE} reports version=${BUILT_VERSION} revision=${BUILT_REVISION} goVersion=go1.26.6 service=fixture-api" \
  "${GOOD_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}"

assert_verify "version mismatch fails" 1 \
  "Dockerfile must declare ARG VERSION" \
  "${GOOD_IMAGE}" '9.9.9' "${BUILT_REVISION}"

assert_verify "revision mismatch fails" 1 \
  "Dockerfile must declare ARG REVISION" \
  "${GOOD_IMAGE}" "${BUILT_VERSION}" 'ffffffffffffffffffffffffffffffffffffffff'

assert_verify "linker flags never wired fails on version" 1 \
  "reports version <empty>, CI built ${BUILT_VERSION}" \
  "${UNSTAMPED_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}"

assert_verify "revision never wired fails on revision" 1 \
  "reports revision <empty>, CI built ${BUILT_REVISION}" \
  "${HALF_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}"

assert_verify "image without --version support fails" 1 \
  "did not answer --version with JSON" \
  "${SILENT_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}" 30 'starting service'

assert_verify "image that never answers times out" 1 \
  "failed or timed out after 2s" \
  "${SLOW_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}" 2

started=${SECONDS}
assert_verify "image that ignores SIGTERM still times out" 1 \
  "failed or timed out after 3s (container stopped)" \
  "${STUBBORN_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}" 3
elapsed=$((SECONDS - started))
printf 'info - SIGTERM-ignoring image returned after %ds\n' "${elapsed}"
if [[ ${elapsed} -gt 15 ]]; then
  record_fail "SIGTERM-ignoring image is bounded" "returned after ${elapsed}s, limit 15s"
else
  record_pass "SIGTERM-ignoring image is bounded"
fi
if [[ -n $(docker ps -aq --filter "${CONTAINER_FILTER}") ]]; then
  record_fail "timed-out container is removed" "$(docker ps -a --filter "${CONTAINER_FILTER}")"
else
  record_pass "timed-out container is removed"
fi

assert_verify "workflow command injection in goVersion is rejected unechoed" 1 \
  "reports a goVersion outside the allowed character set" \
  "${INJECT_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}" 30 'INJECTED'

assert_verify "version outside the allowed characters is rejected unechoed" 1 \
  "reports a version outside the allowed character set" \
  "${BADVERSION_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}" 30 '&& id'

assert_verify "service outside the allowed characters is rejected unechoed" 1 \
  "reports a service outside the allowed character set" \
  "${BADSERVICE_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}" 30 'svc+evil'

# The shim refuses a run without --pull=never, and nothing tagged MISSING_IMAGE exists,
# so this fails locally instead of reaching for a registry.
assert_verify "missing local image fails without a pull" 1 \
  "docker run ${MISSING_IMAGE} --version failed" \
  "${MISSING_IMAGE}" "${BUILT_VERSION}" "${BUILT_REVISION}"

assert_verify "missing IMAGE fails" 1 "IMAGE is required" \
  '' "${BUILT_VERSION}" "${BUILT_REVISION}"

assert_verify "missing EXPECTED_VERSION fails" 1 "EXPECTED_VERSION is required" \
  "${GOOD_IMAGE}" '' "${BUILT_REVISION}"

assert_verify "missing EXPECTED_REVISION fails" 1 "EXPECTED_REVISION is required" \
  "${GOOD_IMAGE}" "${BUILT_VERSION}" ''

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
