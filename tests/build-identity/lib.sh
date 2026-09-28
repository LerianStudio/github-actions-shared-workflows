# shellcheck shell=bash
# Sourced by the build identity suites. Sets WORKFLOW and extract_run_block.

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
WORKFLOW="${REPO_ROOT}/.github/workflows/build.yml"

# Prints the body of the `run: |` block belonging to the step with the given `id`,
# dedented to column zero. Empty output means the step or its block moved, which
# the callers treat as a failure rather than silently testing nothing.
extract_run_block() {
  awk -v want="$1" '
    $0 ~ "^[[:space:]]*id: " want "$" { found = 1; next }
    found && !inrun && /^[[:space:]]*run: \|[[:space:]]*$/ {
      match($0, /^ */); indent = RLENGTH; inrun = 1; next
    }
    inrun {
      if ($0 ~ /^[[:space:]]*$/) { print ""; next }
      match($0, /^ */)
      if (RLENGTH <= indent) exit
      print substr($0, indent + 3)
    }
  ' "${WORKFLOW}"
}
