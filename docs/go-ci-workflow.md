# Go CI Workflow

Reusable workflow for Go continuous integration that runs tests across multiple Go versions and operating systems, performs linting, verifies code formatting, and optionally builds cross-platform binaries.

## Features

- Multi-version Go testing (configurable versions)
- Cross-platform testing (Linux, macOS, Windows)
- golangci-lint with configurable arguments
- Code formatting verification (gofmt + go vet)
- Go module tidiness check
- Go coverage comment integration for PR feedback
- Optional cross-platform binary builds
- Documentation completeness checks
- Aggregate status check for all jobs

## Usage

### Basic Usage

```yaml
name: CI
on:
  push:
    branches: [develop, release-candidate, main]
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
```

### Custom Configuration

```yaml
name: CI
on: [push, pull_request]

jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
    with:
      go_versions: '["1.22", "1.23"]'
      operating_systems: '["ubuntu-latest", "macos-latest"]'
      go_version_lint: '1.23'
      golangci_lint_version: 'latest'
      golangci_lint_args: '--timeout=10m --enable-all'
      enable_coverage_comment: true
      check_docs: true
      check_module_tidy: true
```

### With Cross-Platform Builds

```yaml
name: CI
on: [push, pull_request]

jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
    with:
      enable_cross_platform_build: true
      build_path: './cmd/myapp'
      build_targets: |
        [
          {"os": "linux", "arch": "amd64"},
          {"os": "linux", "arch": "arm64"},
          {"os": "darwin", "arch": "amd64"},
          {"os": "darwin", "arch": "arm64"},
          {"os": "windows", "arch": "amd64"}
        ]
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `go_versions` | JSON array of Go versions to test | No | `["1.21", "1.22", "1.23"]` |
| `operating_systems` | JSON array of OSes to test on | No | `["ubuntu-latest", "macos-latest", "windows-latest"]` |
| `runner_type` | GitHub runner type for non-matrix jobs | No | `ubuntu-latest` |
| `go_version_lint` | Go version for linting | No | `1.23` |
| `build_cmd` | Build command to execute | No | `go build -v ./...` |
| `test_cmd` | Test command to execute | No | `go test -v -race -coverprofile=coverage.txt -covermode=atomic ./...` |
| `enable_coverage_comment` | Enable Go coverage comment in PR | No | `true` |
| `golangci_lint_version` | golangci-lint version | No | `latest` |
| `golangci_lint_args` | Additional golangci-lint arguments | No | `--timeout=5m` |
| `check_docs` | Enable documentation checks | No | `true` |
| `check_module_tidy` | Enable go.mod/go.sum tidiness check | No | `true` |
| `enable_cross_platform_build` | Enable cross-platform builds | No | `false` |
| `build_targets` | JSON array of build targets | No | `[]` (uses defaults) |
| `build_path` | Path to main package | No | `./cmd` |

## Jobs

### test
Runs tests in a matrix across multiple Go versions and operating systems.

### coverage-report
Posts coverage report as PR comment (only runs on pull requests).

### lint
Runs golangci-lint to check code quality.

### build (optional)
Builds cross-platform binaries if `enable_cross_platform_build` is true.

### verify-module
Verifies go.mod and go.sum are tidy.

### check-format
Checks code formatting and runs go vet.

### check-docs
Checks for required documentation files.

### all-checks-pass
Aggregate status check that fails if any required job fails.

## Example Configurations

### Minimal (Defaults)

```yaml
jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
```

### Only Latest Go Version

```yaml
jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
    with:
      go_versions: '["1.23"]'
      operating_systems: '["ubuntu-latest"]'
```

### Skip Documentation Checks

```yaml
jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
    with:
      check_docs: false
```

## Tips

1. Pin to a version tag: Use `@v1.0.0` instead of `@main` for production stability
2. golangci-lint config: Place `.golangci.yml` in your repo root for custom linting rules
3. Custom build targets: Specify exact platforms you need to reduce build time
4. Markdown link check: Add `.github/markdown-link-check-config.json` to configure link validation
5. Coverage comments: Automatically posted to PRs when `enable_coverage_comment` is true

## Related Workflows

- [Go Security](./go-security-workflow.md) - Comprehensive security scanning
- [Go Release](./go-release-workflow.md) - Automated release creation

---

**Last Updated:** 2025-11-22
**Version:** 1.0.0
