#!/usr/bin/env bash

# Runs the s3_upload job's shell steps from go-release.yml as written against a fake
# `aws` that records its arguments: migrations reach both buckets under one key, and a
# denied mirror write fails the step only after every primary write landed. No AWS.

set -euo pipefail

CDPATH=''
RELEASE_WORKFLOW="$(cd -- "$(dirname -- "$0")/../.." && pwd)/.github/workflows/go-release.yml"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/go-release-s3.XXXXXX")
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

extract_step 'Determine environment folder from tag' >"${WORK_DIR}/folder.sh"
extract_step 'Upload files to S3' >"${WORK_DIR}/upload.sh"
MIRRORS=$(sed -n "/^      s3_upload_mirrors:/,/default:/s/^ *default: '\(.*\)'$/\1/p" "${RELEASE_WORKFLOW}")
[[ -s "${WORK_DIR}/folder.sh" && -s "${WORK_DIR}/upload.sh" && -n "${MIRRORS}" ]] || {
  printf 'not ok - could not extract the s3_upload steps or default from %s\n' "${RELEASE_WORKFLOW}" >&2
  exit 1
}

mkdir -p "${WORK_DIR}/bin" "${WORK_DIR}/repo/db/migrations" "${WORK_DIR}/repo/init"
cat >"${WORK_DIR}/bin/aws" <<'EOF'
#!/usr/bin/env bash
printf 'aws %s\n' "$*" >>"${AWS_LOG}"
[[ -z "${AWS_FAIL_ON:-}" || "$*" != *"${AWS_FAIL_ON}"* ]]
EOF
chmod +x "${WORK_DIR}/bin/aws"
touch "${WORK_DIR}/repo/db/migrations/"{1,2,3}.sql "${WORK_DIR}/repo/init/init_data.json"

# Runs both steps for a tag and compares the exit status (0 or nonzero) and the
# recorded aws calls with the expected ones.
assert_calls() {
  local label=$1 tag=$2 uploads=$3 want=$4 expected=$5 folder status=0
  : >"${WORK_DIR}/aws.log"
  : >"${WORK_DIR}/output"
  GITHUB_REF="refs/tags/${tag}" GITHUB_OUTPUT="${WORK_DIR}/output" bash "${WORK_DIR}/folder.sh" >/dev/null
  folder=$(sed -n 's/^folder=//p' "${WORK_DIR}/output")
  (cd "${WORK_DIR}/repo" && PATH="${WORK_DIR}/bin:${PATH}" AWS_LOG="${WORK_DIR}/aws.log" FOLDER="${folder}" \
    S3_UPLOADS="${uploads}" S3_UPLOAD_MIRRORS="${MIRRORS}" AWS_REGION=us-east-2 \
    bash "${WORK_DIR}/upload.sh" >/dev/null 2>&1) || status=$?
  if [[ ${status} -ne 0 ]]; then status=nonzero; fi
  if [[ "${status}" == "${want}" && "$(cat "${WORK_DIR}/aws.log")" == "${expected}" ]]; then
    PASSED=$((PASSED + 1))
    printf 'ok - %s\n' "${label}"
  else
    FAILED=$((FAILED + 1))
    printf 'not ok - %s (exit %s), recorded:\n%s\n' "${label}" "${status}" "$(cat "${WORK_DIR}/aws.log")" >&2
  fi
}

MIGRATIONS='{"s3_bucket":"lerian-migration-files","file_pattern":"db/migrations/*.sql","s3_prefix":"svc/pg"'
P=s3://lerian-migration-files
M=s3://lerian-development-migrations

assert_calls 'beta: migrations land in both buckets, init data only in its own' v1.2.0-beta.3 \
  "[${MIGRATIONS},\"strip_prefix\":\"db/migrations\",\"flatten\":false},{\"s3_bucket\":\"lerian-casdoor-init-data\",\"file_pattern\":\"init/*.json\"}]" 0 \
  "aws s3 cp db/migrations/1.sql ${P}/development/svc/pg/1.sql
aws s3 cp db/migrations/1.sql ${M}/development/svc/pg/1.sql --region us-east-2
aws s3 cp db/migrations/2.sql ${P}/development/svc/pg/2.sql
aws s3 cp db/migrations/2.sql ${M}/development/svc/pg/2.sql --region us-east-2
aws s3 cp db/migrations/3.sql ${P}/development/svc/pg/3.sql
aws s3 cp db/migrations/3.sql ${M}/development/svc/pg/3.sql --region us-east-2
aws s3 cp init/init_data.json s3://lerian-casdoor-init-data/development/"

assert_calls 'rc: a flattened migrations entry is mirrored into staging' v1.2.0-rc.1 "[${MIGRATIONS}}]" 0 \
  "aws s3 cp db/migrations/1.sql ${P}/staging/svc/pg/
aws s3 cp db/migrations/1.sql ${M}/staging/svc/pg/ --region us-east-2
aws s3 cp db/migrations/2.sql ${P}/staging/svc/pg/
aws s3 cp db/migrations/2.sql ${M}/staging/svc/pg/ --region us-east-2
aws s3 cp db/migrations/3.sql ${P}/staging/svc/pg/
aws s3 cp db/migrations/3.sql ${M}/staging/svc/pg/ --region us-east-2"

AWS_FAIL_ON=lerian-development-migrations assert_calls \
  'production: a denied mirror still lets every primary write land, then fails the step' v1.2.0 "[${MIGRATIONS}}]" nonzero \
  "aws s3 cp db/migrations/1.sql ${P}/production/svc/pg/
aws s3 cp db/migrations/1.sql ${M}/production/svc/pg/ --region us-east-2
aws s3 cp db/migrations/2.sql ${P}/production/svc/pg/
aws s3 cp db/migrations/2.sql ${M}/production/svc/pg/ --region us-east-2
aws s3 cp db/migrations/3.sql ${P}/production/svc/pg/
aws s3 cp db/migrations/3.sql ${M}/production/svc/pg/ --region us-east-2"

printf '\n%d passed, %d failed\n' "${PASSED}" "${FAILED}"
[[ ${FAILED} -eq 0 ]]
