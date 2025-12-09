# Go PR Analysis Workflow

Reusable workflow for comprehensive Go PR analysis in monorepos. Handles change detection, linting, security scanning, testing, coverage checks, and build verification - all per changed app using a matrix strategy.

> **Note**: This workflow replaces the standalone `go-coverage-check.yml` and `go-unit-tests.yml` workflows, consolidating all Go PR analysis into a single, unified workflow.

## Features

- **Change Detection**: Automatically detects which apps changed in the PR
- **Matrix Execution**: Runs all checks per changed app in parallel
- **GolangCI-Lint**: Configurable linting with custom version and arguments
- **Security Scanning**: GoSec and govulncheck for vulnerability detection
- **Unit Tests**: Runs tests with race detection and coverage
- **Coverage Check**: Threshold enforcement with PR comments
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@main
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@main
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@main
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
    secrets:
      manage_token: ${{ secrets.GITHUB_TOKEN }}
```

### Minimal (Only Tests and Lint)

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@main
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
| `filter_paths` | JSON array of paths to monitor for changes. If empty, treats repo as single-app. | No | `''` |
| `path_level` | Directory depth level to extract app name | No | `2` |
| `app_name_prefix` | Prefix for app names in matrix output | No | `''` |
| `go_version` | Go version to use | No | `1.23` |
| `golangci_lint_version` | GolangCI-Lint version | No | `v1.62.2` |
| `golangci_lint_args` | Additional golangci-lint arguments | No | `--timeout=5m` |
| `coverage_threshold` | Minimum coverage percentage (0-100) | No | `80` |
| `fail_on_coverage_threshold` | Fail if coverage below threshold | No | `false` |
| `enable_lint` | Enable GolangCI-Lint | No | `true` |
| `enable_security` | Enable security scanning (gosec, govulncheck) | No | `true` |
| `enable_tests` | Enable unit tests | No | `true` |
| `enable_coverage` | Enable coverage check with PR comment | No | `true` |
| `enable_build` | Enable build verification | No | `true` |
| `go_private_modules` | GOPRIVATE pattern for private Go modules (e.g., `github.com/LerianStudio/*`) | No | `''` |

### With Private Go Modules

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@main
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
Detects which apps have changes based on `filter_paths`. Outputs a matrix of changed apps for subsequent jobs.

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

### no-changes
Runs when no Go changes are detected - outputs skip message.

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

## Tips

1. **Pin to version tag**: Use `@v1.0.0` instead of `@main` for production stability
2. **Custom linting**: Place `.golangci.yml` in each app directory for app-specific rules
3. **Coverage threshold**: Start with `fail_on_coverage_threshold: false` and enable once baseline is established
4. **Security findings**: GoSec results appear in GitHub Security tab when SARIF upload succeeds
5. **Performance**: Jobs run in parallel per app - more apps = more parallelism

## Permissions Required

The workflow requires these permissions:
- `contents: read` - To checkout code
- `pull-requests: write` - To post coverage comments
- `security-events: write` - To upload SARIF results

## Related Workflows

- [Go CI](./go-ci-workflow.md) - Multi-version/multi-OS CI pipeline
- [Go Security](./go-security-workflow.md) - Comprehensive security scanning (8 tools)
- [Changed Paths](./changed-paths-workflow.md) - Standalone change detection
- [Build](./build-workflow.md) - Docker image builds
- [Slack Notify](./slack-notify-workflow.md) - Workflow notifications

---

**Last Updated:** 2025-12-09
**Version:** 1.1.0
