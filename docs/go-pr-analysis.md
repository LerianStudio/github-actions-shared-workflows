# Go PR Analysis Workflow

Reusable workflow for comprehensive Go PR analysis in monorepos. Handles change detection, linting, security scanning, testing, coverage checks, and build verification - all per changed app using a matrix strategy.

> **Note**: This workflow replaces the standalone `go-coverage-check.yml` and `go-unit-tests.yml` workflows, consolidating all Go PR analysis into a single, unified workflow.

## Features

- **Change Detection**: Automatically detects which apps changed in the PR
- **Matrix Execution**: Runs all checks per changed app in parallel
- **Makefile Integration**: Auto-detects and uses Makefile targets when available (lint, test, sec, build)
- **GolangCI-Lint**: Configurable linting with custom version and arguments
- **Security Scanning**: GoSec and govulncheck for vulnerability detection
- **Unit Tests**: Runs tests with race detection and coverage
- **Coverage Check**: Threshold enforcement with PR comments
- **Coverage Filtering**: Supports `.ignorecoverunit` file to exclude patterns from coverage
- **Build Verification**: Ensures code compiles successfully
- **Skip Logic**: Gracefully skips when no Go changes detected

## Usage

### Single App Repository

```yaml
name: Go Analysis
on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@tier-1
    secrets: inherit
```

### Monorepo with Multiple Apps

```yaml
name: Go Analysis
on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@tier-1
    with:
      filter_paths: '["apps/api", "apps/worker", "apps/gateway"]'
    secrets: inherit
```

### Full Configuration

```yaml
name: Go Analysis
on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@tier-1
    with:
      filter_paths: '["apps/control-plane", "apps/agent", "apps/lambda-authorizer"]'
      path_level: 2
      app_name_prefix: "platform"
      go_version: "1.23"
      golangci_lint_version: "v1.62.2"
      golangci_lint_args: "--timeout=5m"
      coverage_threshold: 80
      fail_on_coverage_threshold: false
      enable_lint: true
      enable_security: true
      enable_tests: true
      enable_coverage: true
      enable_build: true
      integration_test_runner_type: blacksmith-8vcpu-ubuntu-2404
    secrets: inherit
```

### Minimal (Only Tests and Lint)

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@tier-1
    with:
      filter_paths: '["src/services"]'
      enable_security: false
      enable_coverage: false
      enable_build: false
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner_type` | GitHub runner type | No | `firmino-lxc-runners` |
| `lint_runner_type` | Optional runner override for the Lint jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | No | `''` |
| `test_runner_type` | Optional runner override for the Tests jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | No | `''` |
| `integration_test_runner_type` | Optional runner override for the Integration Tests jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | No | `''` |
| `coverage_runner_type` | Optional runner override for the Coverage jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | No | `''` |
| `build_runner_type` | Optional runner override for the Build jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | No | `''` |
| `filter_paths` | JSON array of paths to monitor for changes. If empty, treats repo as single-app. | No | `''` |
| `path_level` | Directory depth level to extract app name | No | `2` |
| `normalize_to_filter` | Collapse every changed file under a `filter_paths` entry into that one component (`working_dir` = the filter itself) instead of the `path_level`-trimmed directory. With `false`, a change deeper than `path_level` segments inside a filtered component spawns a bogus matrix entry rooted at that subdirectory — no testable package, so no `coverage.txt`, and the coverage job fails with "Artifact not found". | No | `true` |
| `app_name_prefix` | Prefix for app names in matrix output | No | `''` |
| `go_version` | Go version to use | No | `1.23` |
| `golangci_lint_version` | GolangCI-Lint version | No | `v1.62.2` |
| `govulncheck_version` | govulncheck version to install. Pinned rather than `@latest` so an upstream release cannot change what runs here unchosen. Works at any `go_version` — the install step overrides `GOTOOLCHAIN=auto`, the scan still runs under the pinned toolchain | No | `v1.7.0` |
| `golangci_lint_args` | Additional golangci-lint arguments | No | `--timeout=5m` |
| `coverage_threshold` | Minimum coverage percentage (0-100) | No | `80` |
| `fail_on_coverage_threshold` | Fail if coverage below threshold | No | `true` |
| `enable_lint` | Enable GolangCI-Lint | No | `true` |
| `enable_security` | Enable security scanning (gosec, govulncheck) | No | `true` |
| `enable_tests` | Enable unit tests | No | `true` |
| `enable_coverage` | Enable coverage check with PR comment | No | `true` |
| `enable_build` | Enable build verification | No | `true` |
| `go_private_modules` | GOPRIVATE pattern for private Go modules (e.g., `github.com/LerianStudio/*`) | No | `''` |
| `enable_integration_tests` | Enable integration tests job | No | `false` |
| `integration_test_command` | Command to run integration tests | No | `make test-integration` |
| `integration_tests_config` | JSON configuring the integration lane beyond the command: `service`, `test_env` and `guard`. See [Integration tests with a service container](#integration-tests-with-a-service-container). Empty keeps the serviceless, unguarded job | No | `''` |
| `enable_test_determinism` | Enable test determinism check (runs tests multiple times with shuffle) | No | `false` |
| `test_determinism_runs` | Number of times to run tests for determinism check | No | `3` |
| `system_packages` | Space-separated list of apt packages to install before running Go commands (e.g., `"libxml2-dev pkg-config"`). Required for CGO repositories that depend on native system libraries. Installed in all Go jobs (lint, security, tests, build, integration-tests, test-determinism). | No | `''` |
| `enable_slack_notification` | Send the analysis verdict to Slack. Set to `false` in repositories without `SLACK_WEBHOOK_URL` so the job is skipped entirely instead of running just to skip internally | No | `true` |

### With Private Go Modules

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@tier-1
    with:
      filter_paths: '["components/api"]'
      go_private_modules: "github.com/MyOrg/*"
    secrets: inherit
```

## Secrets

Uses `secrets: inherit` pattern. Required secrets:

| Secret | Description | Required When |
|--------|-------------|---------------|
| `MANAGE_TOKEN` | GitHub token for PR comments and private module access | Private modules or PR comments |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Optional |

## Jobs

### detect-changes
Detects which apps have changes based on `filter_paths`, delegating to the [`changed-paths`](../src/config/changed-paths/README.md) composite action. Outputs a matrix of changed apps for subsequent jobs.

### lint
Runs GolangCI-Lint per changed app. Configurable version and arguments.

### security
Runs security scanners per changed app:
- **GoSec**: Static analysis for security issues (uploads SARIF to GitHub Security tab)
- **govulncheck**: Official Go vulnerability database check

### tests
Runs unit tests per changed app with:
- Race detection (`-race`) with `CGO_ENABLED=1`
- Coverage profiling
- Uploads coverage artifacts
- Supports private Go modules via `go_private_modules` input

### coverage
Calculates coverage and posts PR comment per changed app:
- Downloads coverage artifact from `tests` job
- Compares against threshold
- Posts formatted coverage report as PR comment

### build
Verifies code compiles successfully per changed app.

### integration-tests
Runs integration tests per changed app using a configurable command (default: `make test-integration`). Disabled by default — enable with `enable_integration_tests: true`.

Optionally starts a backing service container, exports the suite's environment, and verifies the suite actually ran — see [Integration tests with a service container](#integration-tests-with-a-service-container).

### test-determinism
Runs unit tests multiple times with `-shuffle=on` to detect flaky or order-dependent tests. Always uses `go test` directly (bypasses Makefile) to guarantee shuffle flags are applied. Excludes `/tests/` and `/api/` packages. Disabled by default — enable with `enable_test_determinism: true`.

### no-changes
Runs when no Go changes are detected - outputs skip message.


## Integration tests with a service container

`enable_integration_tests: true` on its own runs the suite on a bare runner. That is enough for suites with no external dependency, but Go integration tests conventionally skip themselves when their backing service is unconfigured:

```go
dsn := os.Getenv("POSTGRES_TEST_URL")
if dsn == "" {
    t.Skip("POSTGRES_TEST_URL not set")
}
```

Under `go test ./...` that skip is invisible: the run is green and the check is named "Integration Tests". A missing job is honest; a green one that ran nothing is a claim.

`integration_tests_config` closes both halves of that gap — it gives the job a database, and it makes a skipped suite fail.

### Schema

```jsonc
{
  "service": {                       // optional — a backing container on the runner
    "image": "postgres:16.13",       // required when `service` is present
    "ports": "5432:5432",            // string, or an array of "host:container"
    "health_cmd": "pg_isready",      // run inside the container until it exits 0
    "health_timeout": 60,            // seconds, default 60
    "env": { "POSTGRES_PASSWORD": "postgres", "POSTGRES_DB": "app" }
  },
  "test_env": {                      // optional — exported to the test step
    "POSTGRES_TEST_URL": "postgres://postgres:postgres@127.0.0.1:5432/app?sslmode=disable"
  },
  "guard": {                         // optional — anti-skip guard
    "packages": "./internal/store/ ./internal/httpapi/",
    "pattern": "AgainstRealPostgres",
    "args": ["-tags=integration"]    // flags the guard's own `go test` needs
  }
}
```

Every key is optional and the three parts are independent: a suite with no external dependency can still use `guard` alone. **Unknown keys are rejected** — with the configuration travelling as a JSON string, a typo must fail loudly rather than be silently dropped.

### Full example

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-validation.yml@tier-1
    with:
      go_version: "1.25.3"
      enable_integration_tests: true
      integration_tests_config: |
        {
          "service": {
            "image": "postgres:16.13",
            "ports": "5432:5432",
            "health_cmd": "pg_isready",
            "env": { "POSTGRES_PASSWORD": "postgres", "POSTGRES_DB": "app" }
          },
          "test_env": {
            "POSTGRES_TEST_URL": "postgres://postgres:postgres@127.0.0.1:5432/app?sslmode=disable"
          },
          "guard": {
            "packages": "./internal/store/ ./internal/httpapi/",
            "pattern": "AgainstRealPostgres"
          }
        }
    secrets: inherit
```

### The guard

When `guard` is set, the job runs `go test <args> -run <pattern> -v -count=1 <package>` **once per package** and fails if a package exits non-zero, reports `--- SKIP`, or reports no `--- PASS` at all.

`guard.args` matters when the suite sits behind a build tag. The guard builds its own invocation, so it does not inherit the flags `integration_test_command` uses: a suite guarded by `//go:build integration` would be invisible to it and reported as "no test matched" immediately after the suite passed. Repeat the tag there — `"args": ["-tags=integration"]`.

One invocation per package is deliberate: a merged log cannot express this, because a package with no matching test emits neither line and another package's pass would cover for it. `-count=1` defeats the test cache, which would otherwise replay a pass recorded when the service *was* available.

### Notes

- **Pin the image to a patch version.** `postgres:16` is mutable and silently becomes 16.14, 16.15…, so "CI matches the deployed planner" quietly stops being true — and a planner difference that passes CI and fails in the cluster is exactly what the job exists to catch. A tagless image raises a warning.
- **Always set `health_cmd`.** Without one, the first connection races the container's startup and the job fails intermittently rather than usefully. Its absence raises a warning.
- **Use throwaway credentials only.** `service.env` and `test_env` values are CI-local; they are never echoed, but they are not secrets storage.
- **`service` uses `docker run`, not a `services:` block.** `services.<id>.env` is a static mapping that cannot be expanded from an input, and a `services:` block cannot be declared conditionally. The job runs on the runner itself, so a published port lands on `localhost` exactly as it would with `services:`. The container is removed under `if: always()`, and its last 200 log lines are printed on the way out.

## How Change Detection Works

1. Compares changed files between `github.event.before` and current SHA
2. Extracts directory paths up to `path_level` depth
3. Filters paths matching `filter_paths` array
4. Builds matrix with `name` and `working_dir` for each changed app

**Example:**

```
filter_paths: '["apps/api", "apps/worker"]'
path_level: 2

Changed files:
- apps/api/handlers/user.go
- apps/api/models/user.go
- apps/worker/jobs/sync.go

Resulting matrix:
[
  {"name": "api", "working_dir": "apps/api"},
  {"name": "worker", "working_dir": "apps/worker"}
]
```

With `app_name_prefix: "myapp"`:
```
[
  {"name": "myapp-api", "working_dir": "apps/api"},
  {"name": "myapp-worker", "working_dir": "apps/worker"}
]
```

## PR Comment Format

Coverage reports are posted as PR comments in this format:

```markdown
## 📊 Unit Test Coverage Report: `platform-api`

| Metric | Value |
|--------|-------|
| **Coverage** | `85.5%` ✅ PASS |
| **Threshold** | `80%` |

---
*Generated by Go PR Analysis workflow*
```

## Makefile Integration

The workflow automatically detects and uses Makefile targets when available, providing consistency between local development and CI pipelines.

### Target Mapping

| Job | Make Target | Fallback (No Makefile) |
|-----|-------------|------------------------|
| Lint | `make lint` | golangci-lint-action |
| Tests | `make coverage-unit` or `make test` | `go test -race -coverprofile=coverage.txt ./...` |
| Security | `make sec SARIF=1` | gosec + govulncheck |
| Build | `make build` | `go build -v ./...` |

### Detection Logic

1. Checks if `Makefile`, `makefile`, or `GNUmakefile` exists in working directory
2. Runs `make -n <target>` to verify target exists (dry-run)
3. Uses make target if available, otherwise falls back to direct commands

### Example Makefile

```makefile
.PHONY: lint test coverage-unit sec build

lint:
	golangci-lint run ./...

test:
	go test -v ./...

coverage-unit:
	go test -v -race -coverprofile=coverage.out -covermode=atomic ./...

sec:
ifdef SARIF
	gosec -fmt sarif -out gosec-report.sarif ./...
else
	gosec ./...
endif
	govulncheck ./...

build:
	go build -v ./...
```

## Coverage Filtering

Exclude files from coverage reports using the `.ignorecoverunit` file. This is useful for excluding generated code, mocks, infrastructure adapters, etc.

### Usage

Create a `.ignorecoverunit` file in your app directory:

```
# Patterns to exclude from coverage
# One pattern per line, glob style

# Auto-generated mocks
*_mock.go

# Infrastructure adapters (tested via integration tests)
*.postgresql.go
*.mongodb.go
*.redis.go

# Bootstrap code
/cmd/
bootstrap.go

# Auto-generated API docs
/api/
swagger.go
```

### Pattern Syntax

- `*.mock.go` - Any file ending in `.mock.go`
- `/cmd/` - Any file in cmd directory
- `bootstrap.go` - Specific file name
- Lines starting with `#` are comments
- Empty lines are ignored

### Default exclusions

When a repo does **not** provide its own `.ignorecoverunit`, the shared workflow applies a built-in default so the most common non-unit-testable paths are excluded out of the box:

```
*_mock.go
/bootstrap/
/cmd/
bootstrap.go
/api/
/test/e2e/
/tests/e2e/
/internal/testutil/
```

Precedence (first match wins): working-directory `.ignorecoverunit` → repository-root `.ignorecoverunit` → built-in default. A repo-provided file fully replaces the default (the two are not merged). To opt out of all exclusions and report full coverage, commit an **empty** `.ignorecoverunit`.

### How It Works

1. After tests run and generate `coverage.txt`, the workflow looks for `.ignorecoverunit` (working dir, then repo root); if neither exists it uses the built-in default above
2. Patterns are converted to regex and used to filter coverage data
3. Filtered coverage is used for threshold checks and PR comments
4. Works regardless of whether Makefile or direct Go commands were used

## Tips

1. **Pin to version tag**: Use `@v1.0.0` instead of `@v1.0.0` for production stability
2. **Custom linting**: Place `.golangci.yml` in each app directory for app-specific rules
3. **Coverage threshold**: Enforced by default (`fail_on_coverage_threshold: true`); set it to `false` to temporarily report coverage without blocking while establishing a baseline
4. **Security findings**: GoSec results appear in GitHub Security tab when SARIF upload succeeds
5. **Performance**: Jobs run in parallel per app - more apps = more parallelism
6. **Makefile consistency**: Use Makefiles to ensure local dev matches CI behavior
7. **Coverage exclusions**: Use `.ignorecoverunit` to exclude generated/infrastructure code from coverage

## Permissions Required

The workflow requires these permissions:
- `actions: read` - To let the gosec action read the workflow run for status/telemetry
- `contents: read` - To checkout code
- `pull-requests: write` - To post coverage comments
- `security-events: write` - To upload SARIF results

## Related Workflows

- [Go CI](./go-ci.md) - Multi-version/multi-OS CI pipeline
- [Go Security](./go-security.md) - Comprehensive security scanning (8 tools)
- [Build](./build.md) - Docker image builds
- [Slack Notify](./slack-notify.md) - Workflow notifications

---

**Last Updated:** 2026-03-12
**Version:** 1.3.0
